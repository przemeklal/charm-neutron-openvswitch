import os
import shutil
import yaml

from charmhelpers.contrib.openstack.neutron import neutron_plugin_attribute
from copy import deepcopy

from charmhelpers.contrib.openstack import context, templating
from charmhelpers.contrib.openstack.utils import (
    git_install_requested,
    git_clone_and_install,
    git_src_dir,
)
from collections import OrderedDict
from charmhelpers.contrib.openstack.utils import (
    os_release,
)
import neutron_ovs_context

BASE_GIT_PACKAGES = [
    'libxml2-dev',
    'libxslt1-dev',
    'openvswitch-switch',
    'python-dev',
    'python-pip',
    'python-setuptools',
    'zlib1g-dev',
]

# ubuntu packages that should not be installed when deploying from git
GIT_PACKAGE_BLACKLIST = [
    'neutron-server',
    'neutron-plugin-openvswitch',
    'neutron-plugin-openvswitch-agent',
]

NOVA_CONF_DIR = "/etc/nova"
NEUTRON_CONF_DIR = "/etc/neutron"
NEUTRON_CONF = '%s/neutron.conf' % NEUTRON_CONF_DIR
NEUTRON_DEFAULT = '/etc/default/neutron-server'
ML2_CONF = '%s/plugins/ml2/ml2_conf.ini' % NEUTRON_CONF_DIR
PHY_NIC_MTU_CONF = '/etc/init/os-charm-phy-nic-mtu.conf'
TEMPLATES = 'templates/'

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
    (PHY_NIC_MTU_CONF, {
        'services': ['os-charm-phy-nic-mtu'],
        'contexts': [neutron_ovs_context.PhyNICMTUContext()],
    }),
])


def determine_packages():
    pkgs = neutron_plugin_attribute('ovs', 'packages', 'neutron')

    if git_install_requested():
        pkgs.extend(BASE_GIT_PACKAGES)
        # don't include packages that will be installed from git
        for p in GIT_PACKAGE_BLACKLIST:
            packages.remove(p)

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
    return resource_map


def restart_map():
    '''
    Constructs a restart map based on charm config settings and relation
    state.
    '''
    return {k: v['services'] for k, v in resource_map().iteritems()}


def git_install(projects_yaml):
    """Perform setup, and install git repos specified in yaml parameter."""
    if git_install_requested():
        git_pre_install()
        git_clone_and_install(projects_yaml, core_project='neutron')
        git_post_install(projects_yaml)


def git_pre_install():
    """Perform pre-install setup."""
    dirs = [
        '/etc/neutron',
        '/etc/neutron/rootwrap.d',
        '/etc/neutron/plugins',
        '/var/lib/neutron',
        '/var/lib/neutron/lock',
        '/var/log/neutron',
    ]

    logs = [
        '/var/log/neutron/server.log',
    ]

    adduser('neutron', shell='/bin/bash', system_user=True)
    add_group('neutron', system_group=True)
    add_user_to_group('neutron', 'neutron')

    for d in dirs:
        mkdir(d, owner='neutron', group='neutron', perms=0700, force=False)

    for l in logs:
        write_file(l, '', owner='neutron', group='neutron', perms=0600)


def git_post_install(projects_yaml):
    """Perform post-install setup."""
    src_etc = os.path.join(git_src_dir(projects_yaml, 'neutron'), 'etc')
    configs = {
        'debug-filters': {
            'src': os.path.join(src_etc, 'neutron/rootwrap.d/debug.filters'),
            'dest': '/etc/neutron/rootwrap.d/debug.filters',
        },
        'openvswitch-plugin-filters': {
            'src': os.path.join(src_etc, 'neutron/rootwrap.d/openvswitch-plugin.filters'),
            'dest': '/etc/neutron/rootwrap.d/openvswitch-plugin.filters',
        },
        'policy': {
            'src': os.path.join(src_etc, 'policy.json'),
            'dest': '/etc/neutron/policy.json',
        },
        'rootwrap': {
            'src': os.path.join(src_etc, 'rootwrap.conf'),
            'dest': '/etc/neutron/rootwrap.conf',
        },
    }

    for conf, files in configs.iteritems():
        shutil.copyfile(files['src'], files['dest'])

    configs_dir = {
        'ml2': {
            'src': os.path.join(src_etc, 'neutron/plugins/ml2/'),
            'dest': '/etc/neutron/plugins/ml2/',
        },
    }

    for conf, dirs in configs_dir.iteritems():
        shutil.copytree(dirs['src'], dirs['dest'])

    #render('neutron-server.default', '/etc/default/neutron-server', {}, perms=0o440)
    #render('neutron_sudoers', '/etc/sudoers.d/neutron_sudoers', {}, perms=0o440)

    neutron_ovs_agent_context = {
        'service_description': 'Neutron OpenvSwitch Plugin Agent',
        'charm_name': 'neutron-openvswitch',
        'process_name': 'neutron-openvswitch-agent',
        'cleanup_process_name': 'neutron-ovs-cleanup',
        'plugin_config': '/etc/neutron/plugins/ml2/ml2_conf.ini',
        'log_file': '/var/log/neutron/openvswitch-agent.log',
    }

    neutron_ovs_cleanup_context = {
        'service_description': 'Neutron OpenvSwitch Cleanup',
        'charm_name': 'neutron-openvswitch',
        'process_name': 'neutron-ovs-cleanup',
        'log_file': '/var/log/neutron/ovs-cleanup.log',
    }

    # NOTE(coreycb): Needs systemd support
    render('upstart/neutron-plugin-openvswitch-agent.upstart',
           '/etc/init/neutron-plugin-openvswitch-agent.conf',
           neutron_ovs_agent_context, perms=0o644)
    render('upstart/neutron-ovs-cleanup.upstart',
           '/etc/init/neutron-ovs-cleanup.conf',
           neutron_ovs_cleanup_context, perms=0o644)

    service_start('neutron-plugin-openvswitch-agent')
