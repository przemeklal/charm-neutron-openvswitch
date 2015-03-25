import os
import uuid
from charmhelpers.core.hookenv import (
    config,
    unit_get,
)
from charmhelpers.contrib.network.ip import (
    get_address_in_network,
)
from charmhelpers.contrib.openstack.ip import resolve_address
from charmhelpers.core.host import list_nics, get_nic_hwaddr
from charmhelpers.contrib.openstack import context
from charmhelpers.core.host import service_running, service_start
from charmhelpers.contrib.network.ovs import add_bridge, add_bridge_port
from charmhelpers.contrib.openstack.utils import get_host_ip
from charmhelpers.contrib.openstack.context import (
    OSContextGenerator,
    NeutronAPIContext,
)

import re

OVS_BRIDGE = 'br-int'
DATA_BRIDGE = 'br-data'


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
        neutron_api_settings = NeutronAPIContext()()
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
        neutron_api_settings = NeutronAPIContext()()
        ovs_ctxt['neutron_security_groups'] = self.neutron_security_groups
        ovs_ctxt['l2_population'] = neutron_api_settings['l2_population']
        ovs_ctxt['distributed_routing'] = neutron_api_settings['enable_dvr']
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
        neutron_api_settings = NeutronAPIContext()()
        ctxt = {}
        if neutron_api_settings['enable_dvr']:
            ctxt['agent_mode'] = 'dvr'
        else:
            ctxt['agent_mode'] = 'legacy'
        return ctxt


SHARED_SECRET = "/etc/neutron/secret.txt"


def get_shared_secret():
    secret = None
    if not os.path.exists(SHARED_SECRET):
        secret = str(uuid.uuid4())
        with open(SHARED_SECRET, 'w') as secret_file:
            secret_file.write(secret)
    else:
        with open(SHARED_SECRET, 'r') as secret_file:
            secret = secret_file.read().strip()
    return secret


class DVRSharedSecretContext(OSContextGenerator):

    def __call__(self):
        if NeutronAPIContext()()['enable_dvr']:
            ctxt = {
                'shared_secret': get_shared_secret(),
                'local_ip': resolve_address(),
            }
        else:
            ctxt = {}
        return ctxt
