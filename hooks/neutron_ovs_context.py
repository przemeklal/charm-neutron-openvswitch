from charmhelpers.core.hookenv import (
    relation_ids,
    related_units,
    relation_get,
    config,
    unit_get,
)
from charmhelpers.core.host import list_nics, get_nic_hwaddr
from charmhelpers.contrib.openstack import context
from charmhelpers.core.host import (
    service_running,
    service_start,
    service_restart,
)
from charmhelpers.contrib.network.ovs import add_bridge, add_bridge_port
from charmhelpers.contrib.openstack.utils import get_host_ip
from charmhelpers.contrib.network.ip import get_address_in_network

import re

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

    # Override if provided in local config
    cfg_net_dev_mtu = config('network-device-mtu')
    if cfg_net_dev_mtu:
        neutron_settings['network_device_mtu'] = cfg_net_dev_mtu

    for rid in relation_ids('neutron-plugin-api'):
        for unit in related_units(rid):
            rdata = relation_get(rid=rid, unit=unit)
            if 'l2-population' not in rdata:
                continue
            neutron_settings = {
                'l2_population': rdata['l2-population'],
                'neutron_security_groups': rdata['neutron-security-groups'],
                'overlay_network_type': rdata['overlay-network-type'],
            }

            # Don't override locally provided value if there is one.
            net_dev_mtu = rdata.get('network-device-mtu')
            if net_dev_mtu and 'network_device_mtu' not in neutron_settings:
                neutron_settings['network_device_mtu'] = net_dev_mtu

            # Override with configuration if set to true
            if config('disable-security-groups'):
                neutron_settings['neutron_security_groups'] = False
            return neutron_settings
    return neutron_settings


def get_bridges_from_mapping():
    """If a bridge mapping is provided, extract the bridge names.

    Returns list of bridges from mapping.
    """
    bridges = []
    mappings = config('bridge-mappings')
    if mappings:
        mappings = mappings.split(' ')
        for m in mappings:
            p = m.partition(':')
            if p[1] == ':':
                bridges.append(p[2])

    return bridges


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

    def get_data_port(self):
        data_ports = config('data-port')
        if not data_ports:
            return None
        hwaddrs = {}
        for nic in list_nics(['eth', 'bond']):
            hwaddrs[get_nic_hwaddr(nic).lower()] = nic
        mac_regex = re.compile(r'([0-9A-F]{2}[:-]){5}([0-9A-F]{2})', re.I)
        for entry in data_ports.split():
            entry = entry.strip().lower()
            if re.match(mac_regex, entry):
                if entry in hwaddrs:
                    return hwaddrs[entry]
            else:
                return entry
        return None

    def _ensure_bridge(self):
        if not service_running('openvswitch-switch'):
            service_start('openvswitch-switch')

        add_bridge(OVS_BRIDGE)
        for br in get_bridges_from_mapping():
            add_bridge(br)
            data_port = self.get_data_port()
            if data_port:
                add_bridge_port(br, data_port, promisc=True)

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

        return ovs_ctxt


class PhyNICMTUContext(context.NeutronPortContext):

    def __call__(self):
        ctxt = {}
        port = config('phy-nics')
        if port:
            ctxt = {"devs": port.replace(' ', '\\n')}
            mtu = config('phy-nic-mtu')
            if mtu:
                ctxt['mtu'] = mtu

        return ctxt
