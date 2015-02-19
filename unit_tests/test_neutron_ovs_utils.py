
from mock import MagicMock, patch
from collections import OrderedDict
import charmhelpers.contrib.openstack.templating as templating

templating.OSConfigRenderer = MagicMock()

import neutron_ovs_utils as nutils
import neutron_ovs_context

from test_utils import (
    CharmTestCase,
)
import charmhelpers
import charmhelpers.core.hookenv as hookenv


TO_PATCH = [
    'os_release',
    'neutron_plugin_attribute',
]

head_pkg = 'linux-headers-3.15.0-5-generic'


def _mock_npa(plugin, attr, net_manager=None):
    plugins = {
        'ovs': {
            'config': '/etc/neutron/plugins/ml2/ml2_conf.ini',
            'driver': 'neutron.plugins.ml2.plugin.Ml2Plugin',
            'contexts': [],
            'services': ['neutron-plugin-openvswitch-agent'],
            'packages': [[head_pkg], ['neutron-plugin-openvswitch-agent']],
            'server_packages': ['neutron-server',
                                'neutron-plugin-ml2'],
            'server_services': ['neutron-server']
        },
    }
    return plugins[plugin][attr]


class TestNeutronOVSUtils(CharmTestCase):

    def setUp(self):
        super(TestNeutronOVSUtils, self).setUp(nutils, TO_PATCH)
        self.neutron_plugin_attribute.side_effect = _mock_npa

    def tearDown(self):
        # Reset cached cache
        hookenv.cache = {}

    @patch.object(charmhelpers.contrib.openstack.neutron, 'os_release')
    @patch.object(charmhelpers.contrib.openstack.neutron, 'headers_package')
    @patch.object(neutron_ovs_context, 'use_dvr')
    def test_determine_packages(self, _use_dvr, _head_pkgs, _os_rel):
        _use_dvr.return_value = False
        _os_rel.return_value = 'trusty'
        _head_pkgs.return_value = head_pkg
        pkg_list = nutils.determine_packages()
        expect = [['neutron-plugin-openvswitch-agent'], [head_pkg]]
        self.assertItemsEqual(pkg_list, expect)

    @patch.object(neutron_ovs_context, 'use_dvr')
    def test_register_configs(self, _use_dvr):
        class _mock_OSConfigRenderer():
            def __init__(self, templates_dir=None, openstack_release=None):
                self.configs = []
                self.ctxts = []

            def register(self, config, ctxt):
                self.configs.append(config)
                self.ctxts.append(ctxt)

        _use_dvr.return_value = False
        self.os_release.return_value = 'trusty'
        templating.OSConfigRenderer.side_effect = _mock_OSConfigRenderer
        _regconfs = nutils.register_configs()
        confs = ['/etc/neutron/neutron.conf',
                 '/etc/neutron/plugins/ml2/ml2_conf.ini']
        self.assertItemsEqual(_regconfs.configs, confs)

    @patch.object(neutron_ovs_context, 'use_dvr')
    def test_resource_map(self, _use_dvr):
        _use_dvr.return_value = False
        _map = nutils.resource_map()
        confs = [nutils.NEUTRON_CONF]
        [self.assertIn(q_conf, _map.keys()) for q_conf in confs]

    @patch.object(neutron_ovs_context, 'use_dvr')
    def test_restart_map(self, _use_dvr):
        _use_dvr.return_value = False
        _restart_map = nutils.restart_map()
        ML2CONF = "/etc/neutron/plugins/ml2/ml2_conf.ini"
        expect = OrderedDict([
            (nutils.NEUTRON_CONF, ['neutron-plugin-openvswitch-agent']),
            (ML2CONF, ['neutron-plugin-openvswitch-agent']),
        ])
        self.assertTrue(len(expect) == len(_restart_map))
        for item in _restart_map:
            self.assertTrue(item in _restart_map)
            self.assertTrue(expect[item] == _restart_map[item])
