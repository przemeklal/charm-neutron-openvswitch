#!/usr/bin/python

import sys
import json

from charmhelpers.core.hookenv import (
    Hooks,
    UnregisteredHookError,
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
    determine_packages,
    register_configs,
    restart_map,
    NEUTRON_SETTINGS,
    ML2_CONF,
)

hooks = Hooks()
CONFIGS = register_configs()


@hooks.hook()
def install():
    apt_update()
    apt_install(determine_packages(), fatal=True)

@restart_on_change(restart_map())
@hooks.hook('config-changed')
def config_changed():
    CONFIGS.write_all()

@hooks.hook('neutron-plugin-relation-joined')
def neutron_plugin_relation_joined():
    relation_set(plugin_conf_file=ML2_CONF, subordinate_configuration=json.dumps(NEUTRON_SETTINGS))

@restart_on_change(restart_map())
@hooks.hook('neutron-plugin-relation-changed')
def neutron_plugin_relation_changed():
    CONFIGS.write_all()

def main():
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))


if __name__ == '__main__':
    main()
