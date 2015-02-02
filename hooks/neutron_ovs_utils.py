from charmhelpers.contrib.openstack.neutron import neutron_plugin_attribute
from copy import deepcopy

from charmhelpers.contrib.openstack import context, templating
from collections import OrderedDict
from charmhelpers.contrib.openstack.utils import (
    os_release,
)
import neutron_ovs_context

NOVA_CONF_DIR = "/etc/nova"
NEUTRON_CONF_DIR = "/etc/neutron"
NEUTRON_CONF = '%s/neutron.conf' % NEUTRON_CONF_DIR
NEUTRON_DEFAULT = '/etc/default/neutron-server'
NEUTRON_L3_AGENT_CONF = "/etc/neutron/l3_agent.ini"
NEUTRON_FWAAS_CONF = "/etc/neutron/fwaas_driver.ini"
ML2_CONF = '%s/plugins/ml2/ml2_conf.ini' % NEUTRON_CONF_DIR

BASE_RESOURCE_MAP = OrderedDict([
    (NEUTRON_CONF, {
        'services': ['neutron-plugin-openvswitch-agent'],
        'contexts': [neutron_ovs_context.OVSPluginContext(),
                     context.AMQPContext(ssl_dir=NEUTRON_CONF_DIR)],
    }),
    (ML2_CONF, {
        'services': ['neutron-plugin-openvswitch-agent'],
        'contexts': [neutron_ovs_context.OVSPluginContext()],
    }),
    (NEUTRON_L3_AGENT_CONF, {
        'services': ['neutron-vpn-agent'],
        'contexts': [neutron_ovs_context.L3AgentContext()],
    }),
    (NEUTRON_FWAAS_CONF, {
        'services': ['neutron-vpn-agent'],
        'contexts': [neutron_ovs_context.L3AgentContext()],
    }),
])
TEMPLATES = 'templates/'


def determine_dvr_packages():
    pkgs = []
    if neutron_ovs_context.use_dvr():
        pkgs = 'neutron-vpn-agent'
    return pkgs


def determine_packages():
    pkgs = neutron_plugin_attribute('ovs', 'packages', 'neutron')
    pkgs.extend(determine_dvr_packages())
    return pkgs


def register_configs(release=None):
    release = release or os_release('neutron-common', base='icehouse')
    configs = templating.OSConfigRenderer(templates_dir=TEMPLATES,
                                          openstack_release=release)
    for cfg, rscs in resource_map().iteritems():
        configs.register(cfg, rscs['contexts'])
    return configs


def resource_map():
    '''
    Dynamically generate a map of resources that will be managed for a single
    hook execution.
    '''
    resource_map = deepcopy(BASE_RESOURCE_MAP)
    if not neutron_ovs_context.use_dvr():
        resource_map.pop(NEUTRON_L3_AGENT_CONF)
    return resource_map


def restart_map():
    '''
    Constructs a restart map based on charm config settings and relation
    state.
    '''
    return {k: v['services'] for k, v in resource_map().iteritems()}
