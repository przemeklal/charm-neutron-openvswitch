
from mock import MagicMock, patch, call
from test_utils import CharmTestCase
import neutron_ovs_context

with patch('charmhelpers.core.hookenv.config') as config:
    config.return_value = 'neutron'
    import neutron_ovs_utils as utils

_reg = utils.register_configs
_map = utils.restart_map

utils.register_configs = MagicMock()
utils.restart_map = MagicMock()

import neutron_ovs_hooks as hooks

utils.register_configs = _reg
utils.restart_map = _map

TO_PATCH = [
    'apt_update',
    'apt_install',
    'apt_purge',
    'config',
    'CONFIGS',
    'determine_packages',
    'determine_dvr_packages',
    'get_shared_secret',
    'log',
    'relation_ids',
    'relation_set',
    'configure_ovs',
    'use_dvr',
]
NEUTRON_CONF_DIR = "/etc/neutron"

NEUTRON_CONF = '%s/neutron.conf' % NEUTRON_CONF_DIR


class NeutronOVSHooksTests(CharmTestCase):

    def setUp(self):
        super(NeutronOVSHooksTests, self).setUp(hooks, TO_PATCH)

        self.config.side_effect = self.test_config.get
        hooks.hooks._config_save = False

    def _call_hook(self, hookname):
        hooks.hooks.execute([
            'hooks/{}'.format(hookname)])

    def test_install_hook(self):
        _pkgs = ['foo', 'bar']
        self.determine_packages.return_value = [_pkgs]
        self._call_hook('install')
        self.apt_update.assert_called_with()
        self.apt_install.assert_has_calls([
            call(_pkgs, fatal=True),
        ])

    @patch.object(neutron_ovs_context, 'use_dvr')
    def test_config_changed(self, _use_dvr):
        _use_dvr.return_value = False
        self._call_hook('config-changed')
        self.assertTrue(self.CONFIGS.write_all.called)
        self.configure_ovs.assert_called_with()

    @patch.object(neutron_ovs_context, 'use_dvr')
    def test_config_changed_dvr(self, _use_dvr):
        _use_dvr.return_value = True
        self.determine_dvr_packages.return_value = ['dvr']
        self._call_hook('config-changed')
        self.apt_update.assert_called_with()
        self.assertTrue(self.CONFIGS.write_all.called)
        self.apt_install.assert_has_calls([
            call(['dvr'], fatal=True),
        ])
        self.configure_ovs.assert_called_with()

    @patch.object(hooks, 'neutron_plugin_joined')
    @patch.object(neutron_ovs_context, 'use_dvr')
    def test_neutron_plugin_api(self, _use_dvr, _plugin_joined):
        _use_dvr.return_value = False
        self.relation_ids.return_value = ['rid']
        self._call_hook('neutron-plugin-api-relation-changed')
        self.configure_ovs.assert_called_with()
        self.assertTrue(self.CONFIGS.write_all.called)
        _plugin_joined.assert_called_with(relation_id='rid')

    def test_neutron_plugin_joined(self):
        self.get_shared_secret.return_value = 'secret'
        self._call_hook('neutron-plugin-relation-joined')
        rel_data = {
            'metadata-shared-secret': 'secret',
        }
        self.relation_set.assert_called_with(
            relation_id=None,
            **rel_data
        )

    def test_amqp_joined(self):
        self._call_hook('amqp-relation-joined')
        self.relation_set.assert_called_with(
            username='neutron',
            vhost='openstack',
            relation_id=None
        )

    def test_amqp_changed(self):
        self.CONFIGS.complete_contexts.return_value = ['amqp']
        self._call_hook('amqp-relation-changed')
        self.assertTrue(self.CONFIGS.write.called_with(NEUTRON_CONF))

    def test_amqp_departed(self):
        self._call_hook('amqp-relation-departed')
        self.assertTrue(self.CONFIGS.write.called_with(NEUTRON_CONF))
