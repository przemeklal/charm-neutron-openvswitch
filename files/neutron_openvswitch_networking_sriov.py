#!/usr/bin/env python3
#
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

import argparse
import os
import sys
import time


def wait_for_vfs(device, numvfs):
    """Wait for the VFs to be created.

    :param str device: path to the NIC
    :param str numvfs: number of VFs to wait for
    :returns: None
    """
    numvfs = int(numvfs)
    created_vfs_number = 0
    while created_vfs_number < numvfs:
        created_vfs = [f for f in os.listdir(device) if f.startswith('virtfn')]
        created_vfs_number = len(created_vfs)
        print('Waiting for {numvfs} VFs to appear in {dev}'.format(
            numvfs=numvfs, dev=device))
        time.sleep(0.05)


def get_totalvfs(device):
    """Get the number of allowed VFs.

    :param str device: Path of the device
    :returns: number of allowed VFs.
    :rtype: str
    """
    path = os.path.join(device, 'sriov_totalvfs')
    with open(path) as f:
        total_vfs = f.read()
    return total_vfs


def find_sriov_devices():
    """Find SR-IOV devices.

    :returns: list of SR-IOV devices' paths
    :rtype: list
    """
    f_name = 'sriov_totalvfs'
    devices = []
    for path, dirs, files in os.walk('/sys/devices'):
        if f_name in files:
            devices.append(path)
    return devices


def write_sriov_numvfs(base_path, numvfs):
    """Write the number of VFs to file.

    :param str base_path: Path of the device
    :param str numvfs: Number of VFs
    :returns: None
    """
    path = os.path.join(base_path, 'sriov_numvfs')
    print('Configuring {numvfs} VFs for {path}'.format(
        numvfs=numvfs, path=path))
    try:
        with open(path, 'w') as f:
            f.write(numvfs)
        wait_for_vfs(base_path, numvfs)
    except OSError as err:
        print(
            'Error while configuring VFs: {err}'.format(err=err))


def configure_vfs(vfs, vfs_blanket='auto', stop=False):
    """Configure the VFs.

    :param dict vfs: list of VFs as dict (e.g. {'eth0': '8', 'eth1': '4'}
    :param str vfs_blanket: blanket config for the VFs
    :param bool stop: If we are stopping
    :returns: None
    """
    if vfs:
        for device, numvfs in vfs.items():
            if stop:
                numvfs = '0'
            base_path = '/sys/class/net/{dev}/device/'.format(dev=device)
            write_sriov_numvfs(base_path, numvfs)
    else:
        sriov_devices = find_sriov_devices()
        for device in sriov_devices:
            total_vfs = get_totalvfs(device)
            if stop:
                vfs_blanket = '0'
            if vfs_blanket == 'auto':
                numvfs = total_vfs
            elif int(vfs_blanket) > int(total_vfs):
                numvfs = total_vfs
            else:
                numvfs = vfs_blanket
            write_sriov_numvfs(device, numvfs)


def restart(vfs, vfs_blanket):
    """Restart the VFs

    :param dict vfs: list of VFs as dict (e.g. {'eth0': '8', 'eth1': '4'}
    :returns: None
    """
    stop(vfs)
    start(vfs, vfs_blanket)


def start(vfs, vfs_blanket):
    """Start the VFs.

    :param dict vfs: list of VFs as dict (e.g. {'eth0': '8', 'eth1': '4'}
    :returns: None
    """
    configure_vfs(vfs, vfs_blanket)


def stop(vfs):
    """Stop the VFs.

    :param dict vfs: list of VFs as dict (e.g. {'eth0': '8', 'eth1': '4'}
    :returns: None
    """
    configure_vfs(vfs, stop=True)


def parse_vfs(vfs=None):
    """Parse VFs from string

    :param dict vfs: string containing the VFs
    :returns: dict of VFs
    :rtype: dict {
        'eth0': '8',
        'eth1': '2'
    }
    """
    if not vfs:
        return {}
    parsed_vfs = {}
    for vf in vfs.split():
        k, v = vf.split(':')
        parsed_vfs[k] = v
    return parsed_vfs


def parse_args(args):
    """Parse the arguments.

    : param list args: list of args
    : returns: the parsed arguments
    : rtype: Namespace
    : raises SystemExit: if there are missing required args
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--start',
        help='Start',
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--stop',
        help='Stop',
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--restart',
        help='Restart',
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--vfs',
        help='VFS List'
    )
    parser.add_argument(
        '--vfs-blanket',
        help='VFS Blanket',
        default='auto'
    )
    return parser.parse_args(args)


def main(args):
    """Main function.

    : param list args: list of arguments
    : returns: 0
    : rtype: int
    """
    args = parse_args(args)
    vfs = parse_vfs(args.vfs)
    if args.restart:
        restart(vfs, args.vfs_blanket)
    elif args.start:
        start(vfs, args.vfs_blanket)
    elif args.stop:
        stop(vfs)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
