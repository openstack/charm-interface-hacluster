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

from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


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

        if relation_data:
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

        """
        relation_data = {k: v for k, v in crm.items() if v}
        self.set_local(**relation_data)
        self.set_remote(**relation_data)
