import os
import uuid
from charmhelpers.core.hookenv import (
    relation_ids,
    related_units,
    relation_get,
    config,
    unit_get,
)
from charmhelpers.contrib.network.ip import (
    get_address_in_network,
    get_ipv4_addr,
    get_ipv6_addr,
    is_bridge_member,
)
from charmhelpers.contrib.openstack.ip import resolve_address
from charmhelpers.core.host import list_nics, get_nic_hwaddr
from charmhelpers.core.strutils import bool_from_string
from charmhelpers.contrib.openstack import context
from charmhelpers.core.host import service_running, service_start
from charmhelpers.contrib.network.ovs import add_bridge, add_bridge_port
from charmhelpers.contrib.openstack.utils import get_host_ip
from charmhelpers.contrib.openstack.context import (
    OSContextGenerator,
    context_complete,
)

import re

OVS_BRIDGE = 'br-int'
DATA_BRIDGE = 'br-data'


def _neutron_api_settings():
    '''
    Inspects current neutron-plugin relation
    '''
    neutron_settings = {
        'neutron_security_groups': False,
        'l2_population': True,
        'overlay_network_type': 'gre',
        'enable_dvr': False,
    }
    for rid in relation_ids('neutron-plugin-api'):
        for unit in related_units(rid):
            rdata = relation_get(rid=rid, unit=unit)
            if 'l2-population' not in rdata:
                continue
            neutron_settings = {
                'l2_population': bool_from_string(rdata['l2-population']),
                'overlay_network_type': rdata['overlay-network-type'],
                'neutron_security_groups': bool_from_string(
                    rdata['neutron-security-groups']
                ),
            }
            if 'enable-dvr' in rdata:
                neutron_settings['enable_dvr'] = bool_from_string(
                    rdata['enable-dvr']
                )
            # Override with configuration if set to true
            if config('disable-security-groups'):
                neutron_settings['neutron_security_groups'] = False
            return neutron_settings
    return neutron_settings


def use_dvr():
    api_settings = _neutron_api_settings()
    if 'enable_dvr' in api_settings:
        return api_settings['enable_dvr']
    else:
        return False


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
        add_bridge(DATA_BRIDGE)
        data_port = self.get_data_port()
        if data_port:
            add_bridge_port(DATA_BRIDGE, data_port, promisc=True)

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
        ovs_ctxt['distributed_routing'] = use_dvr()
        ovs_ctxt['overlay_network_type'] = \
            neutron_api_settings['overlay_network_type']
        # TODO: We need to sort out the syslog and debug/verbose options as a
        # general context helper
        ovs_ctxt['use_syslog'] = conf['use-syslog']
        ovs_ctxt['verbose'] = conf['verbose']
        ovs_ctxt['debug'] = conf['debug']
        return ovs_ctxt


class L3AgentContext(OSContextGenerator):

    def __call__(self):
        neutron_api_settings = _neutron_api_settings()
        ctxt = {}
        if neutron_api_settings['enable_dvr']:
            ctxt['agent_mode'] = 'dvr'
        else:
            ctxt['agent_mode'] = 'legacy'
        return ctxt


class NeutronPortContext(OSContextGenerator):

    def _resolve_port(self, config_key):
        if not config(config_key):
            return None
        hwaddr_to_nic = {}
        hwaddr_to_ip = {}
        for nic in list_nics(['eth', 'bond']):
            hwaddr = get_nic_hwaddr(nic)
            hwaddr_to_nic[hwaddr] = nic
            addresses = get_ipv4_addr(nic, fatal=False) + \
                get_ipv6_addr(iface=nic, fatal=False)
            hwaddr_to_ip[hwaddr] = addresses
        mac_regex = re.compile(r'([0-9A-F]{2}[:-]){5}([0-9A-F]{2})', re.I)
        for entry in config(config_key).split():
            entry = entry.strip()
            if re.match(mac_regex, entry):
                if entry in hwaddr_to_nic and len(hwaddr_to_ip[entry]) == 0:
                    # If the nic is part of a bridge then don't use it
                    if is_bridge_member(hwaddr_to_nic[entry]):
                        continue
                    # Entry is a MAC address for a valid interface that doesn't
                    # have an IP address assigned yet.
                    return hwaddr_to_nic[entry]
            else:
                # If the passed entry is not a MAC address, assume it's a valid
                # interface, and that the user put it there on purpose (we can
                # trust it to be the real external network).
                return entry
        return None


class ExternalPortContext(NeutronPortContext):

    def __call__(self):
        port = self._resolve_port('ext-port')
        if port:
            return {"ext_port": port}
        else:
            return None


class NetworkServiceContext(OSContextGenerator):
    interfaces = ['neutron-network-service']

    def __call__(self):
        for rid in relation_ids('neutron-network-service'):
            for unit in related_units(rid):
                rdata = relation_get(rid=rid, unit=unit)
                ctxt = {
                    'service_protocol':
                    rdata.get('service_protocol') or 'http',
                    'keystone_host': rdata.get('keystone_host'),
                    'service_port': rdata.get('service_port'),
                    'region': rdata.get('region'),
                    'service_tenant': rdata.get('service_tenant'),
                    'service_username': rdata.get('service_username'),
                    'service_password': rdata.get('service_password'),
                }
                if context_complete(ctxt):
                    return ctxt


class DVRSharedSecretContext(OSContextGenerator):

    def get_shared_secret(self):
        secret = None
        if not os.path.exists(self.SHARED_SECRET):
            secret = str(uuid.uuid4())
            with open(self.SHARED_SECRET, 'w') as secret_file:
                secret_file.write(secret)
        else:
            with open(self.SHARED_SECRET, 'r') as secret_file:
                secret = secret_file.read().strip()
        return secret

    def __call__(self):
        self.SHARED_SECRET = "/etc/neutron/secret.txt"
        if use_dvr():
            ctxt = {
                'shared_secret': self.get_shared_secret(),
                'local_ip': resolve_address(),
            }
        else:
            ctxt = {}
        return ctxt
