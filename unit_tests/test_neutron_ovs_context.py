
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
    'add_bridge_port',
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

    @patch('charmhelpers.contrib.openstack.context.NeutronPortContext.'
           'resolve_ports')
    def test_data_port_name(self, mock_resolve_ports):
        self.test_config.set('data-port', 'phybr1:em1')
        mock_resolve_ports.side_effect = lambda ports: ports
        self.assertEquals(context.DataPortContext()(),
                          {'phybr1': 'em1'})

    @patch.object(context, 'get_nic_hwaddr')
    @patch('charmhelpers.contrib.openstack.context.get_nic_hwaddr')
    @patch('charmhelpers.contrib.openstack.context.list_nics')
    def test_data_port_mac(self, list_nics, get_nic_hwaddr, get_nic_hwaddr2):
        machine_machs = {
            'em1': 'aa:aa:aa:aa:aa:aa',
            'eth0': 'bb:bb:bb:bb:bb:bb',
        }
        get_nic_hwaddr2.side_effect = lambda nic: machine_machs[nic]
        absent_mac = "cc:cc:cc:cc:cc:cc"
        config_macs = ("phybr2:%s phybr1:%s" %
                       (absent_mac, machine_machs['em1']))
        self.test_config.set('data-port', config_macs)
        list_nics.return_value = machine_machs.keys()
        get_nic_hwaddr.side_effect = lambda nic: machine_machs[nic]
        self.assertEquals(context.DataPortContext()(),
                          {'phybr1': 'em1'})

    @patch('charmhelpers.contrib.openstack.context.NeutronPortContext.'
           'resolve_ports')
    def test_ensure_bridge_data_port_present(self, mock_resolve_ports):
        self.test_config.set('data-port', 'phybr1:em1')
        self.test_config.set('bridge-mappings', 'phybr1:br-data')

        def add_port(bridge, port, promisc):
            if bridge == 'br-data' and port == 'em1' and promisc is True:
                self.bridge_added = True
                return
            self.bridge_added = False

        mock_resolve_ports.side_effect = lambda ports: ports
        self.add_bridge_port.side_effect = add_port
        context.OVSPluginContext()._ensure_bridge()
        self.assertEquals(self.bridge_added, True)

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
        self.test_relation.set({'neutron-security-groups': 'True',
                                'l2-population': 'True',
                                'network-device-mtu': 1500,
                                'overlay-network-type': 'gre',
                                })
        self.get_host_ip.return_value = '127.0.0.15'
        self.service_running.return_value = False
        napi_ctxt = context.OVSPluginContext()
        expect = {
            'neutron_alchemy_flags': {},
            'neutron_security_groups': True,
            'verbose': True,
            'local_ip': '127.0.0.15',
            'network_device_mtu': 1500,
            'veth_mtu': 1500,
            'config': 'neutron.randomconfig',
            'use_syslog': True,
            'network_manager': 'neutron',
            'debug': True,
            'core_plugin': 'neutron.randomdriver',
            'neutron_plugin': 'ovs',
            'neutron_url': 'https://127.0.0.13:9696',
            'l2_population': True,
            'overlay_network_type': 'gre',
            'bridge_mappings': 'physnet1:br-data'
        }
        self.assertEquals(expect, napi_ctxt())
        self.service_start.assertCalled()

    @patch.object(charmhelpers.contrib.openstack.context, 'config')
    @patch.object(charmhelpers.contrib.openstack.context, 'unit_get')
    @patch.object(charmhelpers.contrib.openstack.context, 'is_clustered')
    @patch.object(charmhelpers.contrib.openstack.context, 'https')
    @patch.object(context.OVSPluginContext, '_save_flag_file')
    @patch.object(context.OVSPluginContext, '_ensure_packages')
    @patch.object(charmhelpers.contrib.openstack.context,
                  'neutron_plugin_attribute')
    @patch.object(charmhelpers.contrib.openstack.context, 'unit_private_ip')
    def test_neutroncc_context_api_rel_disable_security(self,
                                                        _unit_priv_ip, _npa,
                                                        _ens_pkgs, _save_ff,
                                                        _https, _is_clus,
                                                        _unit_get,
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
        self.test_config.set('disable-security-groups', True)
        self.related_units.return_value = ['unit1']
        self.relation_ids.return_value = ['rid2']
        self.test_relation.set({'neutron-security-groups': 'True',
                                'l2-population': 'True',
                                'network-device-mtu': 1500,
                                'overlay-network-type': 'gre',
                                })
        self.get_host_ip.return_value = '127.0.0.15'
        self.service_running.return_value = False
        napi_ctxt = context.OVSPluginContext()
        expect = {
            'neutron_alchemy_flags': {},
            'neutron_security_groups': True,
            'verbose': True,
            'local_ip': '127.0.0.15',
            'veth_mtu': 1500,
            'network_device_mtu': 1500,
            'config': 'neutron.randomconfig',
            'use_syslog': True,
            'network_manager': 'neutron',
            'debug': True,
            'core_plugin': 'neutron.randomdriver',
            'neutron_plugin': 'ovs',
            'neutron_url': 'https://127.0.0.13:9696',
            'l2_population': True,
            'overlay_network_type': 'gre',
            'bridge_mappings': 'physnet1:br-data'
        }
        self.assertEquals(expect, napi_ctxt())
        self.service_start.assertCalled()
