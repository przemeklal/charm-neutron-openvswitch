
from mock import MagicMock, patch, call
from collections import OrderedDict
import charmhelpers.contrib.openstack.templating as templating
from charmhelpers.contrib.openstack import context

templating.OSConfigRenderer = MagicMock()

import neutron_ovs_utils as nutils
import neutron_ovs_context

from test_utils import (
    CharmTestCase,
)
import charmhelpers
import charmhelpers.core.hookenv as hookenv


TO_PATCH = [
    'add_bridge',
    'add_bridge_port',
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


class DummyContext():

    def __init__(self, return_value):
        self.return_value = return_value

    def __call__(self):
        return self.return_value


class TestNeutronOVSUtils(CharmTestCase):

    def setUp(self):
        super(TestNeutronOVSUtils, self).setUp(nutils, TO_PATCH)
        self.neutron_plugin_attribute.side_effect = _mock_npa

    def tearDown(self):
        # Reset cached cache
        hookenv.cache = {}

    @patch.object(nutils, 'use_dvr')
    @patch.object(charmhelpers.contrib.openstack.neutron, 'os_release')
    @patch.object(charmhelpers.contrib.openstack.neutron, 'headers_package')
    def test_determine_packages(self, _head_pkgs, _os_rel, _use_dvr):
        _use_dvr.return_value = False
        _os_rel.return_value = 'trusty'
        _head_pkgs.return_value = head_pkg
        pkg_list = nutils.determine_packages()
        expect = [['neutron-plugin-openvswitch-agent'], [head_pkg]]
        self.assertItemsEqual(pkg_list, expect)

    @patch.object(nutils, 'use_dvr')
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
                 '/etc/neutron/plugins/ml2/ml2_conf.ini',
                 '/etc/init/os-charm-phy-nic-mtu.conf']
        self.assertItemsEqual(_regconfs.configs, confs)

    @patch.object(nutils, 'use_dvr')
    def test_resource_map(self, _use_dvr):
        _use_dvr.return_value = False
        _map = nutils.resource_map()
        svcs = ['neutron-plugin-openvswitch-agent']
        confs = [nutils.NEUTRON_CONF]
        [self.assertIn(q_conf, _map.keys()) for q_conf in confs]
        self.assertEqual(_map[nutils.NEUTRON_CONF]['services'], svcs)

    @patch.object(nutils, 'use_dvr')
    def test_resource_map_dvr(self, _use_dvr):
        _use_dvr.return_value = True
        _map = nutils.resource_map()
        svcs = ['neutron-plugin-openvswitch-agent', 'neutron-metadata-agent',
                'neutron-vpn-agent']
        confs = [nutils.NEUTRON_CONF]
        [self.assertIn(q_conf, _map.keys()) for q_conf in confs]
        self.assertEqual(_map[nutils.NEUTRON_CONF]['services'], svcs)

    @patch.object(nutils, 'use_dvr')
    def test_restart_map(self, _use_dvr):
        _use_dvr.return_value = False
        _restart_map = nutils.restart_map()
        ML2CONF = "/etc/neutron/plugins/ml2/ml2_conf.ini"
        expect = OrderedDict([
            (nutils.NEUTRON_CONF, ['neutron-plugin-openvswitch-agent']),
            (ML2CONF, ['neutron-plugin-openvswitch-agent']),
            (nutils.PHY_NIC_MTU_CONF, ['os-charm-phy-nic-mtu'])
        ])
        self.assertEqual(expect, _restart_map)
        for item in _restart_map:
            self.assertTrue(item in _restart_map)
            self.assertTrue(expect[item] == _restart_map[item])

    @patch.object(context, 'ExternalPortContext')
    def test_configure_ovs_ovs_ext_port(self, _ext_port_ctxt):
        _ext_port_ctxt.return_value = \
            DummyContext(return_value={'ext_port': 'eth0'})
        nutils.configure_ovs()
        self.add_bridge.assert_has_calls([
            call('br-int'),
            call('br-ex'),
            call('br-data')
        ])
        self.add_bridge_port.assert_called_with('br-ex', 'eth0')

    @patch.object(neutron_ovs_context, 'DVRSharedSecretContext')
    def test_get_shared_secret(self, _dvr_secret_ctxt):
        _dvr_secret_ctxt.return_value = \
            DummyContext(return_value={'shared_secret': 'supersecret'})
        self.assertEqual(nutils.get_shared_secret(), 'supersecret')
