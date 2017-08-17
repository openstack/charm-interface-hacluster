#!/usr/bin/python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ipaddress
from six import string_types


class CRM(dict):
    """
    Configuration object for Pacemaker resources for the HACluster
    interface. This class provides access to the supported resources
    available in the 'crm configure' within the HACluster.

    See Also
    --------
    More documentation is available regarding the definitions of
    primitives, clones, and other pacemaker resources at the crmsh
    site at http://crmsh.github.io/man
    """

    # Constants provided for ordering constraints (e.g. the kind value)
    MANDATORY = "Mandatory"
    OPTIONAL = "Optional"
    SERIALIZE = "Serialize"

    # Constants defining weights of constraints
    INFINITY = "inf"
    NEG_INFINITY = "-inf"

    # Constaints aliased to their interpretations for constraints
    ALWAYS = INFINITY
    NEVER = NEG_INFINITY

    def __init__(self, *args, **kwargs):
        self['resources'] = {}
        self['delete_resources'] = []
        self['resource_params'] = {}
        self['groups'] = {}
        self['ms'] = {}
        self['orders'] = {}
        self['colocations'] = {}
        self['clones'] = {}
        self['locations'] = {}
        self['init_services'] = []
        super(CRM, self).__init__(*args, **kwargs)

    def primitive(self, name, agent, description=None, **kwargs):
        """Configures a primitive resource within Pacemaker.

        A primitive is used to describe a resource which should be managed
        by the cluster. Primitives consist of a name, the agent type, and
        various configuration options to the primitive. For example:

            crm.primitive('www8', 'apache',
                          params='configfile=/etc/apache/www8.conf',
                          operations='$id-ref=apache_ops')

        will create the an apache primitive (resource) for the www8 service
        hosted by the Apache HTTP server. The parameters specified can either
        be provided individually (e.g. a string) or as an iterable.

        The following example shows how to specify multiple ops for a drbd
        volume in a Master/Slave configuration::

            ops = ['monitor role=Master interval=60s',
                   'monitor role=Slave interval=300s']

            crm.primitive('r0', 'ocf:linbit:drbd',
                          params='drbd_resource=r0',
                          op=ops)

        Additional arguments may be passed in as kwargs in which the key of
        the kwarg is prepended to the value.

        Parameters
        ----------
        name: str
            the name of the primitive.
        agent: str
            the type of agent to use to monitor the primitive resource
            (e.g. ocf:linbit:drbd).
        description: str, optional, kwarg
            a description about the resource
        params: str or iterable, optional, kwarg
            parameters which are provided to the resource agent
        meta: str or iterable, optional, kwarg
            metadata information for the primitive resource
        utilization: str or iterable, optional, kwarg
            utilization information for the primitive resource
        operations: str or iterable, optional, kwarg
            operations information for the primitive resource in id_spec
            format (e.g. $id=<id> or $id-ref=<id>)
        op: str or iterable, optional, kwarg
            op information regarding the primitive resource. This takes the
            form of '<start|stop|monitor> [<attr>=<value> <attr>=<value> ...]'

        Returns
        -------
        None

        See Also
        --------
        http://crmsh.github.io/man/#cmdhelp_configure_primitive
        """
        resources = self['resources']
        resources[name] = agent

        specs = ''
        if description:
            specs = specs + 'description="%s"' % description

        # Use the ordering specified in the crm manual
        for key in 'params', 'meta', 'utilization', 'operations', 'op':
            if key not in kwargs:
                continue
            specs = specs + (' %s' % self._parse(key, kwargs[key]))

        if specs:
            self['resource_params'][name] = specs

    def _parse(self, prefix, data):
        results = ''
        if isinstance(data, string_types):
            data = [data]

        first = True
        for d in data:
            if first:
                results = results + ' '
                first = False
            results = results + ('%s %s' % (prefix, d))

        return results

    def clone(self, name, resource, description=None, **kwargs):
        """Creates a resource which should run on all nodes.

        Parameters
        ----------
        name: str
            the name of the clone
        resource: str
            the name or id of the resource to clone
        description: str, optional
            text containing a description for the clone
        meta: str or list of str, optional, kwarg
            metadata attributes to assign to the clone
        params: str or list of str, optional, kwarg
            parameters to assign to the clone

        Returns
        -------
        None

        See Also
        --------
        http://crmsh.github.io/man/#cmdhelp_configure_clone
        """
        clone_specs = resource
        if description:
            clone_specs = clone_specs + (' description="%s"' % description)

        for key in 'meta', 'params':
            if key not in kwargs:
                continue
            value = kwargs[key]
            if not value:
                continue
            clone_specs = clone_specs + (' %s' % self._parse(key, value))

        self['clones'][name] = clone_specs

    def colocation(self, name, score=ALWAYS, *resources, **kwargs):
        """Configures the colocation constraints of resources.

        Provides placement constraints regarding resources defined within
        the cluster. Using the colocate function, resource affinity or
        anti-affinity can be defined.

        For example, the following code ensures that the nova-console service
        always runs where the cluster vip is running:

            crm.colocation('console_with_vip', ALWAYS,
                           'nova-console', 'vip')

        The affinity or anti-affinity of resources relationships is be
        expressed in the `score` parameter. A positive score indicates that
        the resources should run on the same node.A score of INFINITY (or
        ALWAYS) will ensure the resources are always run on the same node(s)
        and a score of NEG_INFINITY (or NEVER) ensures that the resources are
        never run on the same node(s).

            crm.colocation('never_apache_with_dummy', NEVER,
                           'apache', 'dummy')

        Any *resources values which are provided are treated as resources which
        the colocation constraint applies to. At least two resources must be
        defined as part of the ordering constraint.

        The resources take the form of <resource_name>[:role]. If the
        colocation constraint applies specifically to a role, this information
        should be included int he resource supplied.

        Parameters
        ----------
        id: str
            id or name of the colocation constraint
        score: str {ALWAYS, INFINITY, NEVER, NEGATIVE_INFINITY} or int
            the score or weight of the colocation constraint. A positive value
            will indicate that the resources should run on the same node. A
            negative value indicates that the resources should run on separate
            nodes.
        resources: str or list
            the list of resources which the colocation constraint applies to.
        node_attribute: str, optional, kwarg
            can be used to run the resources on a set of nodes, not just a
            single node.

        Returns
        -------
        None

        See Also
        --------
        http://crmsh.github.io/man/#cmdhelp_configure_colocation
        """
        specs = '%s: %s' % (score, ' '.join(resources))
        if 'node_attribute' in kwargs:
            specs = specs + (' node-attribute=%s' % kwargs['node_attribute'])
        self['colocations'][name] = specs

    def group(self, name, *resources, **kwargs):
        """Creates a group of resources within Pacemaker.

        The created group includes the list of resources provided in the list
        of resources supplied. For example::

            crm.group('grp_mysql', 'res_mysql_rbd', 'res_mysql_fs',
                      'res_mysql_vip', 'res_mysqld')

        will create the 'grp_mysql' resource group consisting of the
        res_mysql_rbd, res_mysql_fs, res_mysql_vip, and res_mysqld resources.

        Parameters
        ----------
        name: str
            the name of the group resource
        resources: list of str
            the names or ids of resources to include within the group.
        description: str, optional, kwarg
            text to describe the resource
        meta: str or list of str, optional, kwarg
            metadata attributes to assign to the group
        params: str or list of str, optional, kwarg
            parameters to assign to the group

        Returns
        -------
        None

        See Also
        --------
        http://crmsh.github.io/man/#cmdhelp_configure_group
        """
        specs = ' '.join(resources)
        if 'description' in kwargs:
            specs = specs + (' description="' % kwargs['description'])

        for key in 'meta', 'params':
            if key not in kwargs:
                continue
            value = kwargs[key]
            specs = specs + (' %s' % self._parse(key, value))

        self['groups'][name] = specs

    def delete_resource(self, *resources):
        """Deletes one or more objects/resources within Pacemaker.

        Parameters
        ----------
        resources: str or list
            the name or id of the specific resource to delete.

        Returns
        -------
        None

        See Also
        --------
        http://crmsh.github.io/man/#cmdhelp_configure_delete
        """
        self['delete_resources'].extend(resources)

    def init_services(self, *resources):
        """Specifies that the service(s) is an init or upstart service.

        Services (resources) which are noted as upstart services are
        disabled, stopped, and left to pacemaker to manage the resource.

        Parameters
        ----------
        resources: str or list of str, varargs
            The resources which should be noted as init services.

        Returns
        -------
        None
        """
        self['init_services'].extend(resources)

    def ms(self, name, resource, description=None, **kwargs):
        """Create a master/slave resource type.

        The following code provides an example of creating a master/slave
        resource on drbd disk1::

            crm.ms('disk1', 'drbd1', meta='notify=true globally-unique=false')

        Parameters
        ----------
        name: str
            the name or id of the master resource
        resource: str
            the name or id of the resource which now ha a master/slave
            assocation tied to it.
        description: str, optional
            a textual description of the master resource
        meta: str or list of strs, optional, kwargs
            strings defining the metadata for the master/slave resource type
        params: str or list of strs, optional, kwargs
            parameter strings which should be passed to the master/slave
            resource creation

        Returns
        -------
        None

        See Also
        --------
        http://crmsh.github.io/man/#cmdhelp_configure_ms
        """
        specs = resource
        if description:
            specs = specs + (' description="%s"' % description)

        for key in 'meta', 'params':
            if key not in kwargs:
                continue
            value = kwargs[key]
            specs = specs + (' %s' % self._parse(key, value))

        self['ms'][name] = specs

    def location(self, name, resource, **kwargs):
        """Defines the preference of nodes for the given resource.

        The location constraitns consist of one or more rules which specify
        a score to be awarded if the rules match.

        Parameters
        ----------
        name: str
            the name or id of the location constraint
        resource: str
            the name, id, resource, set, tag, or resoruce pattern defining the
            set of resources which match the location placement constraint.
        attributes: str or list str, optional, kwarg
            attributes which should be assigned to the location constraint
        rule: str or list of str, optional, kwarg
            the rule(s) which define the location constraint rules when
            selecting a location to run the resource.

        Returns
        -------
        None

        See Also
        --------
        http://crmsh.github.io/man/#cmdhelp_configure_location
        """
        specs = resource

        # Check if there are attributes assigned to the location and if so,
        # format the spec string with the attributes
        if 'attributes' in kwargs:
            attrs = kwargs['attributes']
            if isinstance(attrs, string_types):
                attrs = [attrs]
            specs = specs + (' %s' % ' '.join(attrs))

        if 'rule' in kwargs:
            rules = kwargs['rule']
            specs = specs + (' %s' % self._parse('rule', rules))

        self['locations'][name] = specs

    def order(self, name, score=None, *resources, **kwargs):
        """Configures the ordering constraints of resources.

        Provides ordering constraints to resources defined in a Pacemaker
        cluster which affect the way that resources are started, stopped,
        promoted, etc. Basic ordering is provided by simply specifying the
        ordering name and an ordered list of the resources which the ordering
        constraint applies to.

        For example, the following code ensures that the apache resource is
        started after the ClusterIP is started::

            hacluster.order('apache-after-ip', 'ClusterIP', 'apache')

        By default, the ordering constraint will specify that the ordering
        constraint is mandatory. The constraint behavior can be specified
        using the 'score' keyword argument, e.g.::

            hacluster.order('apache-after-ip', score=hacluster.OPTIONAL,
                            'ClusterIP', 'apache')

        Any *resources values which are provided are treated as resources which
        the ordering constraint applies to. At least two resources must be
        defined as part of the ordering constraint.

        The resources take the form of <resource_name>[:<action>]. If the
        ordering constraint applies to a specific action for the resource,
        this information should be included in the resource supplied.

        Parameters
        ----------
        name: str
            the id or name of the order constraint
        resoures: str or list of strs in varargs format
            the resources the ordering constraint applies to. The ordering
            of the list of resources is used to provide the ordering.
        score: {MANDATORY, OPTIONAL, SERIALIZED}, optional
            the score of the ordering constraint.
        symmetrical: boolean, optional, kwarg
            when True, then the services for the resources will be stopped in
            the reverse order. The default value for this is True.

        Returns
        -------
        None

        See Also
        --------
        http://crmsh.github.io/man/#cmdhelp_configure_order
        """
        specs = ''
        if score:
            specs = '%s:' % score

        specs = specs + (' %s' % ' '.join(resources))
        if 'symmetrical' in kwargs:
            specs = specs + (' symmetrical=' % kwargs['symmetrical'])

        self['orders'][name] = specs

    def add(self, resource_desc):
        """Adds a resource descriptor object to the CRM configuration.

        Adds a `ResourceDescriptor` object to the CRM configuration which
        understands how to configure the resource itself. The
        `ResourceDescriptor` object needs to know how to interact with this
        CRM class in order to properly configure the pacemaker resources.

        The minimum viable resource descriptor object will implement a method
        which takes a reference parameter to this CRM in order to configure
        itself.

        Parameters
        ----------
        resource_desC: ResourceDescriptor
            an object which provides an abstraction of a monitored resource
            within pacemaker.

        Returns
        -------
        None
        """
        method = getattr(resource_desc, 'configure_resource', None)
        if not callable(method):
            raise ValueError('Invalid resource_desc. The "configure_resource"'
                             ' function has not been defined.')

        method(self)


class ResourceDescriptor(object):
    """
    A ResourceDescriptor provides a logical resource or concept and knows
    how to configure pacemaker.
    """

    def configure_resource(self, crm):
        """Configures the logical resource(s) within the CRM.

        This is the callback method which is invoked by the CRM in order
        to allow this ResourceDescriptor to fully configure the logical
        resource.

        For example, a Virtual IP may provide a standard abstraction and
        configure the specific details under the covers.
        """
        pass


class InitService(ResourceDescriptor):
    def __init__(self, service_name, init_service_name, clone=True):
        """Class for managing init resource

        :param service_name: string - Name of service
        :param init_service_name: string - Name service uses in init system
        :param clone: bool - clone service across all units
        :returns: None
        """
        self.service_name = service_name
        self.init_service_name = init_service_name
        self.clone = clone

    def configure_resource(self, crm):
        """"Configure new init system service resource in crm

        :param crm: CRM() instance - Config object for Pacemaker resources
        :returns: None
        """
        res_key = 'res_{}_{}'.format(
            self.service_name.replace('-', '_'),
            self.init_service_name.replace('-', '_'))
        res_type = 'lsb:{}'.format(self.init_service_name)
        crm.primitive(res_key, res_type, op='monitor interval="5s"')
        crm.init_services(self.init_service_name)
        if self.clone:
            clone_key = 'cl_{}'.format(res_key)
            crm.clone(clone_key, res_key)


class VirtualIP(ResourceDescriptor):
    def __init__(self, service_name, vip, nic=None, cidr=None):
        """Class for managing VIP resource

        :param service_name: string - Name of service
        :param vip: string - Virtual IP to be managed
        :param nic: string - Network interface to bind vip to
        :param cidr: string - Netmask for vip
        :returns: None
        """
        self.service_name = service_name
        self.vip = vip
        self.nic = nic
        self.cidr = cidr

    def configure_resource(self, crm):
        """Configure new vip resource in crm

        :param crm: CRM() instance - Config object for Pacemaker resources
        :returns: None
        """
        vip_key = 'res_{}_{}_vip'.format(self.service_name, self.nic)
        ipaddr = ipaddress.ip_address(self.vip)
        if isinstance(ipaddr, ipaddress.IPv4Address):
            res_type = 'ocf:heartbeat:IPaddr2'
            res_params = 'ip="{}"'.format(self.vip)
        else:
            res_type = 'ocf:heartbeat:IPv6addr'
            res_params = 'ipv6addr="{}"'.format(self.vip)
            vip_params = 'ipv6addr'
            vip_key = 'res_{}_{}_{}_vip'.format(self.service_name, self.nic,
                                                vip_params)

        if self.nic:
            res_params = '{} nic="{}"'.format(res_params, self.nic)
        if self.cidr:
            res_params = '{} cidr_netmask="{}"'.format(res_params, self.cidr)
        crm.primitive(vip_key, res_type, params=res_params)
