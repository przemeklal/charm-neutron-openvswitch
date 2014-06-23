from charmhelpers.core.hookenv import (
    relation_ids,
    related_units,
    relation_get,
    config,
    unit_get,
)

from charmhelpers.contrib.openstack import context
from charmhelpers.core.host import service_running, service_start
from charmhelpers.contrib.network.ovs import add_bridge
from charmhelpers.contrib.openstack.utils import get_host_ip
OVS_BRIDGE = 'br-int'


def _neutron_security_groups():
    '''
    Inspects current neutron-plugin relation and determine if neutron-api has
    instructed us to use neutron security groups.
    '''
    for rid in relation_ids('neutron-plugin-api'):
        for unit in related_units(rid):
            sec_group = relation_get('neutron-security-groups',
                                     rid=rid,
                                     unit=unit)
            if sec_group is not None:
                return sec_group
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
        # TODO: We need to sort out the syslog and debug/verbose options as a
        # general context helper
        ovs_ctxt['use_syslog'] = conf['use-syslog']
        ovs_ctxt['verbose'] = conf['verbose']
        ovs_ctxt['debug'] = conf['debug']
        return ovs_ctxt
