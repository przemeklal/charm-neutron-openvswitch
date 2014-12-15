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
