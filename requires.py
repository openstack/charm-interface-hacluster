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

import relations.hacluster.common
from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes
from charms.reactive.helpers import data_changed


class HAClusterRequires(RelationBase):
    # The hacluster charm is a subordinate charm and really only works
    # for a single service to the HA Cluster relation, therefore set the
    # expected scope to be GLOBAL.
    scope = scopes.GLOBAL

    @hook('{requires:hacluster}-relation-joined')
    def joined(self):
        self.set_state('{relation_name}.connected')

    @hook('{requires:hacluster}-relation-changed')
    def changed(self):
        self.set_state('{relation_name}.available')

    @hook('{requires:hacluster}-relation-{broken,departed}')
    def departed(self):
        self.remove_state('{relation_name}.available')
        self.remove_state('{relation_name}.connected')

    def bind_on(self, iface=None, mcastport=None):
        relation_data = {}
        if iface:
            relation_data['corosync_bindiface'] = iface
        if mcastport:
            relation_data['corosync_mcastport'] = mcastport

        if relation_data and data_changed('hacluster-bind_on', relation_data):
            self.set_local(**relation_data)
            self.set_remote(**relation_data)

    def manage_resources(self, crm):
        """
        Request for the hacluster to manage the resources defined in the
        crm object.

            res = CRM()
            res.primitive('res_neutron_haproxy', 'lsb:haproxy',
                          op='monitor interval="5s"')
            res.init_services('haproxy')
            res.clone('cl_nova_haproxy', 'res_neutron_haproxy')

            hacluster.manage_resources(crm)

        :param crm: CRM() instance - Config object for Pacemaker resources
        :returns: None
        """
        relation_data = {k: v for k, v in crm.items() if v}
        if data_changed('hacluster-manage_resources', relation_data):
            self.set_local(**relation_data)
            self.set_remote(**relation_data)

    def bind_resources(self, iface, mcastport=None):
        """Inform the ha subordinate about each service it should manage. The
        child class specifies the services via self.ha_resources

        :param iface: string - Network interface to bind to
        :param mcastport: int - Multicast port corosync should use for cluster
                                management traffic
        """
        if mcastport is None:
            mcastport = 4440
        resources = self.get_local('resources')
        self.bind_on(iface=iface, mcastport=mcastport)
        self.manage_resources(resources)

    def add_vip(self, name, vip, iface, netmask):
        """Add a VirtualIP object for each user specified vip to self.resources

        :param name: string - Name of service
        :param vip: string - Virtual IP to be managed
        :param iface: string - Network interface to bind vip to
        :param netmask: string - Netmask for vip
        :returns: None
        """
        resource_dict = self.get_local('resources')
        if resource_dict:
            resources = relations.hacluster.common.CRM(**resource_dict)
        else:
            resources = relations.hacluster.common.CRM()
        resources.add(
            relations.hacluster.common.VirtualIP(
                name,
                vip,
                nic=iface,
                cidr=netmask,))

        # Vip Group
        group = 'grp_{}_vips'.format(name)
        vip_res_group_members = []
        if resource_dict:
            vip_resources = resource_dict.get('resources')
            if vip_resources:
                for vip_res in vip_resources:
                    if 'vip' in vip_res:
                        vip_res_group_members.append(vip_res)
                resources.group(group, *vip_res_group_members)

        self.set_local(resources=resources)

    def add_init_service(self, name, service, clone=True):
        """Add a InitService object for haproxy to self.resources

        :param name: string - Name of service
        :param service: string - Name service uses in init system
        :returns: None
        """
        resource_dict = self.get_local('resources')
        if resource_dict:
            resources = relations.hacluster.common.CRM(**resource_dict)
        else:
            resources = relations.hacluster.common.CRM()
        resources.add(
            relations.hacluster.common.InitService(name, service, clone))
        self.set_local(resources=resources)
