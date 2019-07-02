# Copyright 2019 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

import unittest
from unittest.mock import (
    call,
    mock_open,
    patch
)
import files.neutron_openvswitch_networking_sriov as net_sriov


class NeutronOVSNetworkingSriovTest(unittest.TestCase):

    def test_parse_args(self):
        results = net_sriov.parse_args(['--start'])
        self.assertEqual(results.start, True)
        results = net_sriov.parse_args(['--stop'])
        self.assertEqual(results.stop, True)
        results = net_sriov.parse_args(['--restart'])
        self.assertEqual(results.restart, True)
        args = [
            '--start',
            '--vfs',
            'eth0:8 eth1:4',
            '--vfs-blanket',
            '8'
        ]
        results = net_sriov.parse_args(args)
        self.assertEqual(results.vfs, 'eth0:8 eth1:4')
        self.assertEqual(results.vfs_blanket, '8')

    def test_parse_vfs(self):
        vfs = ''
        result = net_sriov.parse_vfs(vfs)
        expected = {}
        self.assertEqual(result, expected)
        vfs = 'eth0:8 eth1:8'
        result = net_sriov.parse_vfs(vfs)
        expected = {
            'eth0': '8',
            'eth1': '8'
        }
        self.assertEqual(result, expected)

    @patch('files.neutron_openvswitch_networking_sriov.write_sriov_numvfs')
    def test_configure_vfs_with_vfs(self, m_write_vfs):
        vfs = {
            'eth0': '8'
        }
        net_sriov.configure_vfs(vfs)
        m_write_vfs.assert_called_once_with(
            '/sys/class/net/eth0/device/',
            '8'
        )

    @patch('files.neutron_openvswitch_networking_sriov.get_totalvfs')
    @patch('files.neutron_openvswitch_networking_sriov.find_sriov_devices')
    @patch('files.neutron_openvswitch_networking_sriov.write_sriov_numvfs')
    def test_configure_vfs_with_blanket_auto(
            self,
            m_write_vfs,
            m_find,
            m_totvfs):
        m_find.return_value = [
            '/dev/one',
            '/dev/two'
        ]
        m_totvfs.return_value = '8'
        net_sriov.configure_vfs({}, 'auto')
        m_write_vfs.assert_has_calls([
            call('/dev/one', '8'),
            call('/dev/two', '8')
        ])

    @patch('files.neutron_openvswitch_networking_sriov.get_totalvfs')
    @patch('files.neutron_openvswitch_networking_sriov.find_sriov_devices')
    @patch('files.neutron_openvswitch_networking_sriov.write_sriov_numvfs')
    def test_configure_vfs_with_blanket_too_big(
            self,
            m_write_vfs,
            m_find,
            m_totvfs):
        m_find.return_value = [
            '/dev/one',
            '/dev/two'
        ]
        m_totvfs.return_value = '2'
        net_sriov.configure_vfs({}, '8')
        m_write_vfs.assert_has_calls([
            call('/dev/one', '2'),
            call('/dev/two', '2')
        ])

    @patch('files.neutron_openvswitch_networking_sriov.get_totalvfs')
    @patch('files.neutron_openvswitch_networking_sriov.find_sriov_devices')
    @patch('files.neutron_openvswitch_networking_sriov.write_sriov_numvfs')
    def test_configure_vfs_with_blanket_smaller_than_totalvfs(
            self,
            m_write_vfs,
            m_find,
            m_totvfs):
        m_find.return_value = [
            '/dev/one',
            '/dev/two'
        ]
        m_totvfs.return_value = '8'
        net_sriov.configure_vfs({}, '2')
        m_write_vfs.assert_has_calls([
            call('/dev/one', '2'),
            call('/dev/two', '2')
        ])

    @patch('time.sleep')
    @patch('os.listdir')
    def test_wait_for_vfs(self, m_listdir, m_sleep):
        dev_list = [
            'subsystem_device',
            'subsystem_vendor',
            'uevent',
            'vendor',
            'virtfn0',
            'virtfn1',
            'virtfn2',
            'virtfn3',
        ]
        m_listdir.return_value = dev_list
        net_sriov.wait_for_vfs('dev', '4')
        m_sleep.assert_called_once_with(0.05)

    @patch('os.walk')
    def test_find_sriov_devices(self, m_walk):
        m_walk.return_value = [
            ('/one', ('dir1', 'dir2'), ('file')),
            ('/one/dir1', (), ('sriov_totalvfs')),
            ('/one/dir2', (), ('sriov_totalvfs'))
        ]
        results = net_sriov.find_sriov_devices()
        expected = [
            '/one/dir1',
            '/one/dir2'
        ]
        self.assertEqual(results, expected)

    @patch('builtins.open', new_callable=mock_open)
    def test_get_totalvfs(self, m_open):
        net_sriov.get_totalvfs('/dev/some')
        m_open.assert_called_once_with(
            '/dev/some/sriov_totalvfs'
        )

    @patch('files.neutron_openvswitch_networking_sriov.wait_for_vfs')
    @patch('builtins.open', new_callable=mock_open)
    def test_write_sriov_numvfs(self, m_open, m_wait_vfs):
        net_sriov.write_sriov_numvfs('/dev/sriov', '8')
        m_open.assert_called_once_with(
            '/dev/sriov/sriov_numvfs',
            'w'
        )
        m_wait_vfs.assert_called_once_with(
            '/dev/sriov',
            '8'
        )

    @patch('files.neutron_openvswitch_networking_sriov.start')
    @patch('files.neutron_openvswitch_networking_sriov.stop')
    def test_restart(self, m_stop, m_start):
        net_sriov.restart([], 'auto')
        m_stop.assert_called_once_with([])
        m_start.assert_called_once_with([], 'auto')

    @patch('files.neutron_openvswitch_networking_sriov.configure_vfs')
    def test_start(self, m_config):
        net_sriov.start([], 'auto')
        m_config.assert_called_once_with([], 'auto')

    @patch('files.neutron_openvswitch_networking_sriov.configure_vfs')
    def test_stop(self, m_config):
        net_sriov.stop([])
        m_config.assert_called_once_with([], stop=True)

    @patch('files.neutron_openvswitch_networking_sriov.restart')
    def test_main_with_restart(self, m_restart):
        args = ['--restart', '--vfs', 'eth0:8 eth1:2', '--vfs-blanket', 'auto']
        net_sriov.main(args)
        vfs = {
            'eth0': '8',
            'eth1': '2'
        }
        vfs_blanket = 'auto'
        m_restart.assert_called_once_with(vfs, vfs_blanket)

    @patch('files.neutron_openvswitch_networking_sriov.start')
    def test_main_with_start(self, m_start):
        args = ['--start', '--vfs', 'eth0:8 eth1:2', '--vfs-blanket', 'auto']
        net_sriov.main(args)
        vfs = {
            'eth0': '8',
            'eth1': '2'
        }
        vfs_blanket = 'auto'
        m_start.assert_called_once_with(vfs, vfs_blanket)

    @patch('files.neutron_openvswitch_networking_sriov.stop')
    def test_main_with_stop(self, m_stop):
        args = ['--stop', '--vfs', 'eth0:8 eth1:2', '--vfs-blanket', 'auto']
        net_sriov.main(args)
        vfs = {
            'eth0': '8',
            'eth1': '2'
        }
        m_stop.assert_called_once_with(vfs)
