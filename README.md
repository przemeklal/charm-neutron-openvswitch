# Overview

This subordinate charm provides the Neutron OpenvSwitch configuration for a compute node.

Once deployed it takes over the management of the Neutron base and plugin configuration on the compute node.

# Usage

To deploy (partial deployment of linked charms only):

    juju deploy rabbitmq-server
    juju deploy neutron-api
    juju deploy nova-compute
    juju deploy neutron-openvswitch
    juju add-relation neutron-openvswitch nova-compute
    juju add-relation neutron-openvswitch neutron-api
    juju add-relation neutron-openvswitch rabbitmq-server

Note that the rabbitmq-server can optionally be a different instance of the rabbitmq-server charm than used by OpenStack Nova:

    juju deploy rabbitmq-server rmq-neutron
    juju add-relation neutron-openvswitch rmq-neutron
    juju add-relation neutron-api rmq-neutron

The neutron-api and neutron-openvswitch charms must be related to the same instance of the rabbitmq-server charm.

# Restrictions

It should only be used with OpenStack Icehouse and above and requires a seperate neutron-api service to have been deployed.

# Disabling security group management

WARNING: this feature allows you to effectively disable security on your cloud!

This charm has a configuration option to allow users to disable any per-instance security group management; this must used with neutron-security-groups enabled in the neutron-api charm and could be used to turn off security on selected set of compute nodes:

    juju deploy neutron-openvswitch neutron-openvswitch-insecure
    juju set neutron-openvswitch-insecure disable-security-groups=True
    juju deploy nova-compute nova-compute-insecure
    juju add-relation nova-compute-insecure neutron-openvswitch-insecure
    ...

These compute nodes could then be accessed by cloud users via use of host aggregates with specific flavors to target instances to hypervisors with no per-instance security.

# Deploying from source

The minimal openstack-origin-git config required to deploy from source is:

  openstack-origin-git:
      "{'neutron':
           {'repository': 'git://git.openstack.org/openstack/neutron.git',
            'branch': 'stable/icehouse'}}"

If you specify a 'requirements' repository, it will be used to update the
requirements.txt files of all other git repos that it applies to, before
they are installed:

  openstack-origin-git:
      "{'requirements':
           {'repository': 'git://git.openstack.org/openstack/requirements.git',
            'branch': 'master'},
        'neutron':
           {'repository': 'git://git.openstack.org/openstack/neutron.git',
            'branch': 'master'}}"

Note that there are only two key values the charm knows about for the outermost
dictionary: 'neutron' and 'requirements'. These repositories must correspond to
these keys. If the requirements repository is specified, it will be installed
first. The neutron repository is always installed last.  All other repostories
will be installed in between.

NOTE(coreycb): The following is temporary to keep track of the full list of
current tip repos (may not be up-to-date).

  openstack-origin-git:
      "{'requirements':
           {'repository': 'git://git.openstack.org/openstack/requirements.git',
            'branch': 'master'},
        'neutron-fwaas':
           {'repository': 'git://git.openstack.org/openstack/neutron-fwaas.git',
            'branch': 'master'},
        'neutron-lbaas':
           {'repository: 'git://git.openstack.org/openstack/neutron-lbaas.git',
            'branch': 'master'},
        'neutron-vpnaas':
           {'repository: 'git://git.openstack.org/openstack/neutron-vpnaas.git',
            'branch': 'master'},
        'keystonemiddleware:
           {'repository': 'git://git.openstack.org/openstack/keystonemiddleware.git',
            'branch: 'master'},
        'oslo-concurrency':
           {'repository': 'git://git.openstack.org/openstack/oslo.concurrency.git',
            'branch: 'master'},
        'oslo-config':
           {'repository': 'git://git.openstack.org/openstack/oslo.config.git',
            'branch: 'master'},
        'oslo-context':
           {'repository': 'git://git.openstack.org/openstack/oslo.context.git',
            'branch: 'master'},
        'oslo-db':
           {'repository': 'git://git.openstack.org/openstack/oslo.db.git',
            'branch: 'master'},
        'oslo-i18n':
           {'repository': 'git://git.openstack.org/openstack/oslo.i18n.git',
            'branch: 'master'},
        'oslo-messaging':
           {'repository': 'git://git.openstack.org/openstack/oslo.messaging.git',
            'branch: 'master'},
        'oslo-middleware:
           {'repository': 'git://git.openstack.org/openstack/oslo.middleware.git',
            'branch': 'master'},
        'oslo-rootwrap':
           {'repository': 'git://git.openstack.org/openstack/oslo.rootwrap.git',
            'branch: 'master'},
        'oslo-serialization':
           {'repository': 'git://git.openstack.org/openstack/oslo.serialization.git',
            'branch: 'master'},
        'oslo-utils':
           {'repository': 'git://git.openstack.org/openstack/oslo.utils.git',
            'branch: 'master'},
        'pbr':
           {'repository': 'git://git.openstack.org/openstack-dev/pbr.git',
            'branch: 'master'},
        'python-keystoneclient':
           {'repository': 'git://git.openstack.org/openstack/python-keystoneclient.git',
            'branch: 'master'},
        'python-neutronclient':
           {'repository': 'git://git.openstack.org/openstack/python-neutronclient.git',
            'branch: 'master'},
        'python-novaclient':
           {'repository': 'git://git.openstack.org/openstack/python-novaclient.git',
            'branch: 'master'},
        'stevedore':
           {'repository': 'git://git.openstack.org/openstack/stevedore.git',
            'branch: 'master'},
        'neutron':
           {'repository': 'git://git.openstack.org/openstack/neutron.git',
            'branch': 'master'}}"
