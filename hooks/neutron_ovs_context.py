from charmhelpers.core.hookenv import (
    relation_ids,
    related_units,
    relation_get,
    config,
    unit_get,
)
from charmhelpers.core.strutils import bool_from_string
from charmhelpers.contrib.openstack import context
from charmhelpers.core.host import (
    service_running,
    service_start,
    service_restart,
)
from charmhelpers.contrib.network.ovs import add_bridge, add_bridge_port
from charmhelpers.contrib.openstack.utils import get_host_ip
from charmhelpers.contrib.network.ip import get_address_in_network
from charmhelpers.contrib.openstack.neutron import (
    parse_bridge_mappings,
    parse_data_port_mappings,
    parse_vlan_range_mappings,
)
from charmhelpers.core.host import (
    get_nic_hwaddr,
)
OVS_BRIDGE = 'br-int'


def _neutron_api_settings():
    '''
    Inspects current neutron-plugin relation
    '''
    neutron_settings = {
        'neutron_security_groups': False,
        'l2_population': True,
        'overlay_network_type': 'gre',
    }

    for rid in relation_ids('neutron-plugin-api'):
        for unit in related_units(rid):
            rdata = relation_get(rid=rid, unit=unit)
            if 'l2-population' in rdata:
                neutron_settings.update({
                    'l2_population': bool_from_string(rdata['l2-population']),
                    'overlay_network_type': rdata['overlay-network-type'],
                    'neutron_security_groups':
                        bool_from_string(rdata['neutron-security-groups'])
                })

            # Override with configuration if set to true
            if config('disable-security-groups'):
                neutron_settings['neutron_security_groups'] = False

            net_dev_mtu = rdata.get('network-device-mtu')
            if net_dev_mtu:
                neutron_settings['network_device_mtu'] = net_dev_mtu

    return neutron_settings


class DataPortContext(context.NeutronPortContext):

    def __call__(self):
        ports = config('data-port')
        if ports:
            portmap = parse_data_port_mappings(ports)
            ports = portmap.values()
            resolved = self.resolve_ports(ports)
            normalized = {get_nic_hwaddr(port): port for port in resolved
                          if port not in ports}
            normalized.update({port: port for port in resolved
                               if port in ports})
            if resolved:
                return {bridge: normalized[port] for bridge, port in
                        portmap.iteritems() if port in normalized.keys()}

        return None


class OVSPluginContext(context.NeutronContext):
    interfaces = []

    @property
    def plugin(self):
        return 'ovs'

    @property
    def network_manager(self):
        return 'neutron'

    @property
    def neutron_security_groups(self):
        neutron_api_settings = _neutron_api_settings()
        return neutron_api_settings['neutron_security_groups']

    def _ensure_bridge(self):
        if not service_running('openvswitch-switch'):
            service_start('openvswitch-switch')

        add_bridge(OVS_BRIDGE)

        portmaps = DataPortContext()()
        bridgemaps = parse_bridge_mappings(config('bridge-mappings'))
        for provider, br in bridgemaps.iteritems():
            add_bridge(br)

            if not portmaps or br not in portmaps:
                continue

            add_bridge_port(br, portmaps[br], promisc=True)

        service_restart('os-charm-phy-nic-mtu')

    def ovs_ctxt(self):
        # In addition to generating config context, ensure the OVS service
        # is running and the OVS bridge exists. Also need to ensure
        # local_ip points to actual IP, not hostname.
        ovs_ctxt = super(OVSPluginContext, self).ovs_ctxt()
        if not ovs_ctxt:
            return {}

        self._ensure_bridge()

        conf = config()
        ovs_ctxt['local_ip'] = \
            get_address_in_network(config('os-data-network'),
                                   get_host_ip(unit_get('private-address')))
        neutron_api_settings = _neutron_api_settings()
        ovs_ctxt['neutron_security_groups'] = self.neutron_security_groups
        ovs_ctxt['l2_population'] = neutron_api_settings['l2_population']
        ovs_ctxt['overlay_network_type'] = \
            neutron_api_settings['overlay_network_type']
        # TODO: We need to sort out the syslog and debug/verbose options as a
        # general context helper
        ovs_ctxt['use_syslog'] = conf['use-syslog']
        ovs_ctxt['verbose'] = conf['verbose']
        ovs_ctxt['debug'] = conf['debug']

        net_dev_mtu = neutron_api_settings.get('network_device_mtu')
        if net_dev_mtu:
            # neutron.conf
            ovs_ctxt['network_device_mtu'] = net_dev_mtu
            # ml2 conf
            ovs_ctxt['veth_mtu'] = net_dev_mtu

        mappings = config('bridge-mappings')
        if mappings:
            ovs_ctxt['bridge_mappings'] = mappings

        vlan_ranges = config('vlan-ranges')
        vlan_range_mappings = parse_vlan_range_mappings(config('vlan-ranges'))
        if vlan_ranges:
            providers = vlan_range_mappings.keys()
            ovs_ctxt['network_providers'] = ' '.join(providers)
            ovs_ctxt['vlan_ranges'] = vlan_ranges

        return ovs_ctxt


class PhyNICMTUContext(DataPortContext):
    """Context used to apply settings to neutron data-port devices"""

    def __call__(self):
        ctxt = {}
        mappings = super(PhyNICMTUContext, self).__call__()
        if mappings and mappings.values():
            ports = mappings.values()
            neutron_api_settings = _neutron_api_settings()
            mtu = neutron_api_settings.get('network_device_mtu')
            if mtu:
                ctxt['devs'] = '\\n'.join(ports)
                ctxt['mtu'] = mtu

        return ctxt
