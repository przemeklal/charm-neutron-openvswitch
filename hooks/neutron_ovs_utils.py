from charmhelpers.contrib.openstack.neutron import neutron_plugin_attribute
from copy import deepcopy
from charmhelpers.contrib.openstack import templating
from collections import OrderedDict
from charmhelpers.contrib.openstack.utils import (
        os_release,
)
import neutron_ovs_context

NOVA_CONF_DIR = "/etc/nova"
NEUTRON_CONF_DIR = "/etc/neutron"
NEUTRON_CONF = "%s/neutron.conf" % NEUTRON_CONF_DIR
ML2_CONF = '%s/plugins/ml2/ml2_conf.ini' % NEUTRON_CONF_DIR
NEUTRON_DEFAULT = '/etc/default/neutron-server'

BASE_RESOURCE_MAP = OrderedDict([
    (ML2_CONF, {
        'services': ['neutron-plugin-openvswitch-agent'],
        'contexts': [neutron_ovs_context.OVSPluginContext()],
    }),
])
TEMPLATES = 'templates/'
NEUTRON_SERVICE_PLUGINS=['neutron.services.l3_router.l3_router_plugin.L3RouterPlugin',
                         'neutron.services.firewall.fwaas_plugin.FirewallPlugin',
                         'neutron.services.loadbalancer.plugin.LoadBalancerPlugin',
                         'neutron.services.vpn.plugin.VPNDriverPlugin',
                         'neutron.services.metering.metering_plugin.MeteringPlugin']
NEUTRON_SETTINGS = {
        "neutron": {
            NEUTRON_CONF: {
                "sections": {
                    "DEFAULT": [
                        ('core_plugin', 'neutron.plugins.ml2.plugin.Ml2Plugin'),
                        ('service_plugins', ','.join(NEUTRON_SERVICE_PLUGINS)),
                    ],
                    "COMMENT": [
                        ('comment1', 'Warning: some settings controlled by subordinate neutron-openvswitch'),
                    ]
                } 
            },
            NEUTRON_DEFAULT: {
                "sections": {
                    "DEFAULT": [
                        ('NEUTRON_PLUGIN_CONFIG', ML2_CONF),
                    ],
                    "COMMENT": [
                        ('comment1', 'Warning: some settings controlled by subordinate neutron-openvswitch'),
                    ]
                } 
            }
        }
}

def determine_packages():
    ovs_pkgs = []
    pkgs = neutron_plugin_attribute('ovs', 'packages',
                                    'neutron')
    for pkg in pkgs:
        ovs_pkgs.extend(pkg)

    return set(ovs_pkgs)

def register_configs(release=None):
    release = release or os_release('neutron-common')
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
    return resource_map

def restart_map():
    '''
    Constructs a restart map based on charm config settings and relation
    state.
    '''
    return {k: v['services'] for k, v in resource_map().iteritems()}
