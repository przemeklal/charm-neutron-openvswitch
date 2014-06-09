from charmhelpers.core.hookenv import (
            relation_ids,
            related_units,
            relation_get,
            is_relation_made,
            config,
            unit_get,
            log,
)

from charmhelpers.contrib.openstack import context
from charmhelpers.core.host import service_running, service_start
from charmhelpers.contrib.network.ovs import add_bridge
from charmhelpers.contrib.openstack.utils import get_host_ip
OVS_BRIDGE = 'br-int'

class OSContextError(Exception):
    pass

def _neutron_security_groups():
    '''
    Inspects current neutron-plugin relation and determine if nova-c-c has
    instructed us to use neutron security groups.
    '''
    for rid in relation_ids('neutron-plugin'):
        for unit in related_units(rid):
            return relation_get('neutron_security_groups',rid=rid, unit=unit)
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
    def save_nova_flag(self):
        return False

    @property
    def neutron_security_groups(self):
        return _neutron_security_groups()

    def _ensure_bridge(self):
        if not service_running('openvswitch-switch'):
            service_start('openvswitch-switch')
        add_bridge(OVS_BRIDGE)

    def ovs_ctxt(self):
        # In addition to generating config context, ensure the OVS service
        # is running and the OVS bridge exists. Also need to ensure
        # local_ip points to actual IP, not hostname.
        ovs_ctxt = super(OVSPluginContext, self).ovs_ctxt()
        if not ovs_ctxt:
            return {}

        self._ensure_bridge()

        conf = config()
        ovs_ctxt['local_ip'] = get_host_ip(unit_get('private-address'))
        ovs_ctxt['neutron_security_groups'] = self.neutron_security_groups
        ovs_ctxt['use_syslog'] = conf['use-syslog']
        return ovs_ctxt
