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
    juju set neutron-openvswitch-insecure disable-security-groups=True prevent-arp-spoofing=False
    juju deploy nova-compute nova-compute-insecure
    juju add-relation nova-compute-insecure neutron-openvswitch-insecure
    ...

These compute nodes could then be accessed by cloud users via use of host aggregates with specific flavors to target instances to hypervisors with no per-instance security.

# Deploying from source

The minimum openstack-origin-git config required to deploy from source is:

    openstack-origin-git: include-file://neutron-juno.yaml

    neutron-juno.yaml
        repositories:
        - {name: requirements,
           repository: 'git://github.com/openstack/requirements',
           branch: stable/juno}
        - {name: neutron,
           repository: 'git://github.com/openstack/neutron',
           branch: stable/juno}

Note that there are only two 'name' values the charm knows about: 'requirements'
and 'neutron'. These repositories must correspond to these 'name' values.
Additionally, the requirements repository must be specified first and the
neutron repository must be specified last. All other repostories are installed
in the order in which they are specified.

The following is a full list of current tip repos (may not be up-to-date):

    openstack-origin-git: include-file://neutron-master.yaml

    neutron-master.yaml
        repositories:
        - {name: requirements,
           repository: 'git://github.com/openstack/requirements',
           branch: master}
        - {name: oslo-concurrency,
           repository: 'git://github.com/openstack/oslo.concurrency',
           branch: master}
        - {name: oslo-config,
           repository: 'git://github.com/openstack/oslo.config',
           branch: master}
        - {name: oslo-context,
           repository: 'git://github.com/openstack/oslo.context',
           branch: master}
        - {name: oslo-db,
           repository: 'git://github.com/openstack/oslo.db',
           branch: master}
        - {name: oslo-i18n,
           repository: 'git://github.com/openstack/oslo.i18n',
           branch: master}
        - {name: oslo-messaging,
           repository: 'git://github.com/openstack/oslo.messaging',
           branch: master}
        - {name: oslo-middleware,
           repository': 'git://github.com/openstack/oslo.middleware',
           branch: master}
        - {name: oslo-rootwrap',
           repository: 'git://github.com/openstack/oslo.rootwrap',
           branch: master}
        - {name: oslo-serialization,
           repository: 'git://github.com/openstack/oslo.serialization',
           branch: master}
        - {name: oslo-utils,
           repository: 'git://github.com/openstack/oslo.utils',
           branch: master}
        - {name: pbr,
           repository: 'git://github.com/openstack-dev/pbr',
           branch: master}
        - {name: stevedore,
           repository: 'git://github.com/openstack/stevedore',
           branch: 'master'}
        - {name: python-keystoneclient,
           repository: 'git://github.com/openstack/python-keystoneclient',
           branch: master}
        - {name: python-neutronclient,
           repository: 'git://github.com/openstack/python-neutronclient',
           branch: master}
        - {name: python-novaclient,
           repository': 'git://github.com/openstack/python-novaclient',
           branch: master}
        - {name: keystonemiddleware,
           repository: 'git://github.com/openstack/keystonemiddleware',
           branch: master}
        - {name: neutron-fwaas,
           repository': 'git://github.com/openstack/neutron-fwaas',
           branch: master}
        - {name: neutron-lbaas,
           repository: 'git://github.com/openstack/neutron-lbaas',
           branch: master}
        - {name: neutron-vpnaas,
           repository: 'git://github.com/openstack/neutron-vpnaas',
           branch: master}
        - {name: neutron,
           repository: 'git://github.com/openstack/neutron',
           branch: master}

# Network Spaces support

This charm supports the use of Juju Network Spaces, allowing the charm to be bound to network space configurations managed directly by Juju.  This is only supported with Juju 2.0 and above.

Open vSwitch endpoints can be configured using the 'data' extra-binding, ensuring that tunnel traffic is routed across the correct host network interfaces:

    juju deploy neutron-openvswitch --bind "data=data-space"

alternatively these can also be provided as part of a juju native bundle configuration:

    neutron-openvswitch:
      charm: cs:xenial/neutron-openvswitch
      bindings:
        data: data-space

NOTE: Spaces must be configured in the underlying provider prior to attempting to use them.

NOTE: Existing deployments using os-data-network configuration options will continue to function; this option is preferred over any network space binding provided if set.

# DPDK fast packet processing support

For OpenStack Mitaka running on Ubuntu 16.04, its possible to use experimental DPDK userspace network acceleration with Open vSwitch and OpenStack.

Currently, this charm supports use of DPDK enabled devices in bridges supporting connectivity to provider networks.

To use DPDK, you'll need to have supported network cards in your server infrastructure (see [dpdk-nics][DPDK documentation]);  DPDK must be enabled and configured during deployment of the charm, for example:

    neutron-openvswitch:
        enable-dpdk: True
        data-port: "br-phynet1:a8:9d:21:cf:93:fc br-phynet2:a8:9d:21:cf:93:fd br-phynet3:a8:9d:21:cf:93:fe"

As devices are not typically named consistently across servers, multiple instances of each bridge -> mac address mapping can be provided; the charm deals with resolution of the set of bridge -> port mappings that are required for each individual unit of the charm.

DPDK requires the use of hugepages, which is not directly configured in the neutron-openvswitch charm; Hugepage configuration can either be done by providing kernel boot command line options for individual servers using MAAS or using the 'hugepages' configuration option of the nova-compute charm:

    nova-compute:
        hugepages: 50%

By default, the charm will configure Open vSwitch/DPDK to consume a processor core + 1G of RAM from each NUMA node on the unit being deployed; this can be tuned using the dpdk-socket-memory and dpdk-socket-cores configuration options of the charm.  The userspace kernel driver can be configured using the dpdk-driver option.  See config.yaml for more details.

**NOTE:** Changing dpdk-socket-* configuration options will trigger a restart of Open vSwitch, which currently causes connectivity to running instances to be lost - connectivity can only be restored with a stop/start of each instance.

**NOTE:** Enabling DPDK support automatically disables security groups for instances.

[dpdk-nics]: http://dpdk.org/doc/nics
