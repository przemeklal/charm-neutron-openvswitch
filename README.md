Overview                                                                                                                                                                                                      
--------

This subordinate charm provides the Neutron OVS configuration for a compute
node. Oncde deployed it takes over the management of the neutron configuration
and plugin configuration on the compute node. It expects three relations:

1) Relation with principle compute node
2) Relation with message broker. If a single message broker is being used for 
   the openstack deployemnt then it can relat to that. If a seperate neutron 
   message broker is being used it should relate to that.
3) Relation with neutron-api principle charm (not nova-cloud-controller)

Restrictions:
------------

It should only be used with Icehouse and above and requires a seperate
neutron-api service to have been deployed.
