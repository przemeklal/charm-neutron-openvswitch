#!/usr/bin/python

import sys

from charmhelpers.core.hookenv import (
    Hooks,
    UnregisteredHookError,
    config,
    log,
    relation_set,
)

from charmhelpers.core.host import (
    restart_on_change
)

from charmhelpers.fetch import (
    apt_install, apt_update
)

from neutron_ovs_utils import (
    configure_ovs,
    determine_packages,
    determine_dvr_packages,
    get_shared_secret,
    register_configs,
    restart_map,
)

hooks = Hooks()
CONFIGS = register_configs()


@hooks.hook()
def install():
    apt_update()
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_install(pkg, fatal=True)


@hooks.hook('neutron-network-service-relation-changed')
@hooks.hook('neutron-plugin-relation-changed')
@hooks.hook('neutron-plugin-api-relation-changed')
@hooks.hook('config-changed')
@restart_on_change(restart_map())
def config_changed():
    if determine_dvr_packages():
        apt_update()
        apt_install(determine_dvr_packages(), fatal=True)
    configure_ovs()
    CONFIGS.write_all()


@hooks.hook('neutron-plugin-relation-joined')
def neutron_plugin_joined(relation_id=None):
    rel_data = {
        'metadata-shared-secret': get_shared_secret()
    }
    relation_set(relation_id=relation_id, **rel_data)


@hooks.hook('amqp-relation-joined')
def amqp_joined(relation_id=None):
    relation_set(relation_id=relation_id,
                 username=config('rabbit-user'),
                 vhost=config('rabbit-vhost'))


@hooks.hook('amqp-relation-changed')
@hooks.hook('amqp-relation-departed')
@restart_on_change(restart_map())
def amqp_changed():
    if 'amqp' not in CONFIGS.complete_contexts():
        log('amqp relation incomplete. Peer not ready?')
        return
    CONFIGS.write_all()


def main():
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))


if __name__ == '__main__':
    main()
