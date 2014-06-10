#!/usr/bin/python
import uuid
import sys
import json

from charmhelpers.core.hookenv import (
    Hooks,
    UnregisteredHookError,
    log,
    relation_set,
    relation_ids,
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
)

hooks = Hooks()
CONFIGS = register_configs()


@hooks.hook()
def install():
    apt_update()
    apt_install(determine_packages(), fatal=True)

@hooks.hook('config-changed')
@restart_on_change(restart_map())
def config_changed():
    CONFIGS.write_all()
    [neutron_plugin_relation_joined(rid) for rid in relation_ids('neutron-plugin')]

@hooks.hook('neutron-plugin-relation-joined')
def neutron_plugin_relation_joined(remote_restart=True):
    if remote_restart:
        comment =  ('restart', 'Restart Trigger: ' + str(uuid.uuid4()))
        for conf in NEUTRON_SETTINGS['neutron']:
            if 'sections' in NEUTRON_SETTINGS['neutron'][conf] and \
               'COMMENT' in NEUTRON_SETTINGS['neutron'][conf]['sections']:
                NEUTRON_SETTINGS['neutron'][conf]['sections']['COMMENT'].append(comment)
    relation_set(subordinate_configuration=json.dumps(NEUTRON_SETTINGS))

@hooks.hook('neutron-plugin-relation-changed')
@restart_on_change(restart_map())
def neutron_plugin_relation_changed(remote_restart=True):
    CONFIGS.write_all()
    if remote_restart:
        comment =  ('restart', 'Restart Trigger: ' + str(uuid.uuid4()))
        for conf in NEUTRON_SETTINGS['neutron']:
            if 'sections' in NEUTRON_SETTINGS['neutron'][conf] and \
               'COMMENT' in NEUTRON_SETTINGS['neutron'][conf]['sections']:
                NEUTRON_SETTINGS['neutron'][conf]['sections']['COMMENT'].append(comment)
    relation_set(subordinate_configuration=json.dumps(NEUTRON_SETTINGS))

def main():
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))


if __name__ == '__main__':
    main()
