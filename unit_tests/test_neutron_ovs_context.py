
from test_utils import CharmTestCase
from mock import patch
import neutron_ovs_context as context
import charmhelpers
TO_PATCH = [
    'relation_get',
    'relation_ids',
    'related_units',
    'config',
    'unit_get',
    'add_bridge',
    'service_running',
    'service_start',
    'get_host_ip',
]


class OVSPluginContextTest(CharmTestCase):

    def setUp(self):
        super(OVSPluginContextTest, self).setUp(context, TO_PATCH)
        self.relation_get.side_effect = self.test_relation.get
        self.config.side_effect = self.test_config.get
        self.test_config.set('debug', True)
        self.test_config.set('verbose', True)
        self.test_config.set('use-syslog', True)

    def tearDown(self):
        super(OVSPluginContextTest, self).tearDown()

    @patch.object(charmhelpers.contrib.openstack.context, 'config')
    @patch.object(charmhelpers.contrib.openstack.context, 'unit_get')
    @patch.object(charmhelpers.contrib.openstack.context, 'is_clustered')
    @patch.object(charmhelpers.contrib.openstack.context, 'https')
    @patch.object(context.OVSPluginContext, '_save_flag_file')
    @patch.object(context.OVSPluginContext, '_ensure_packages')
    @patch.object(charmhelpers.contrib.openstack.context,
                  'neutron_plugin_attribute')
    @patch.object(charmhelpers.contrib.openstack.context, 'unit_private_ip')
    def test_neutroncc_context_api_rel(self, _unit_priv_ip, _npa, _ens_pkgs,
                                       _save_ff, _https, _is_clus, _unit_get,
                                       _config):
        def mock_npa(plugin, section, manager):
            if section == "driver":
                return "neutron.randomdriver"
            if section == "config":
                return "neutron.randomconfig"
        _npa.side_effect = mock_npa
        _config.return_value = 'ovs'
        _unit_get.return_value = '127.0.0.13'
        _unit_priv_ip.return_value = '127.0.0.14'
        _is_clus.return_value = False
        self.related_units.return_value = ['unit1']
        self.relation_ids.return_value = ['rid2']
        self.test_relation.set({'neutron-security-groups': 'yes'})
        self.get_host_ip.return_value = '127.0.0.15'
        self.service_running.return_value = False
        napi_ctxt = context.OVSPluginContext()
        expect = {
            'neutron_alchemy_flags': {},
            'neutron_security_groups': 'yes',
            'verbose': True,
            'local_ip': '127.0.0.15',
            'config': 'neutron.randomconfig',
            'use_syslog': True,
            'network_manager': 'neutron',
            'debug': True,
            'core_plugin': 'neutron.randomdriver',
            'neutron_plugin': 'ovs',
            'neutron_url': 'https://127.0.0.13:9696'
        }
        self.assertEquals(expect, napi_ctxt())
        self.service_start.assertCalled()
