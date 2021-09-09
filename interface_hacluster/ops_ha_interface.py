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
# Copyright 2021 Ubuntu
# See LICENSE file for licensing details.

import hashlib
import json
import interface_hacluster.common as common

from ops.framework import (
    StoredState,
    EventBase,
    ObjectEvents,
    EventSource,
    Object)


class HAServiceReadyEvent(EventBase):
    pass


class HAServiceEvents(ObjectEvents):
    ha_ready = EventSource(HAServiceReadyEvent)


class HAServiceRequires(Object, common.ResourceManagement):

    on = HAServiceEvents()
    _stored = StoredState()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.relation_name = relation_name
        self.framework.observe(
            charm.on[self.relation_name].relation_changed,
            self._on_relation_changed)
        self._stored.set_default(
            resources={})

    def get_local(self, key, default=None):
        key = '%s.%s' % ('local-data', key)
        json_value = getattr(self._stored, key, None)
        if json_value:
            return json.loads(json_value)
        if default:
            return default
        return None

    def set_local(self, key=None, value=None, data=None, **kwdata):
        if data is None:
            data = {}
        if key is not None:
            data[key] = value
        data.update(kwdata)
        if not data:
            return
        for k, v in data.items():
            setattr(
                self._stored,
                'local-data.{}'.format(k),
                json.dumps(v))

    def _on_relation_changed(self, event):
        if self.is_clustered():
            self.on.ha_ready.emit()

    def data_changed(self, data_id, data, hash_type='md5'):
        key = 'data_changed.%s' % data_id
        alg = getattr(hashlib, hash_type)
        serialized = json.dumps(data, sort_keys=True).encode('utf8')
        old_hash = self.get_local(key)
        new_hash = alg(serialized).hexdigest()
        self.set_local(key, new_hash)
        return old_hash != new_hash

    def set_remote(self, key=None, value=None, data=None, **kwdata):
        if data is None:
            data = {}
        if key is not None:
            data[key] = value
        data.update(kwdata)
        if not data:
            return
        for relation in self.framework.model.relations[self.relation_name]:
            for k, v in data.items():
                # The reactive framework copes with integer values but the ops
                # framework insists on strings so convert them.
                if isinstance(v, int):
                    v = str(v)
                relation.data[self.model.unit][k] = v

    def get_remote_all(self, key, default=None):
        """Return a list of all values presented by remote units for key"""
        values = []
        for relation in self.framework.model.relations[self.relation_name]:
            for unit in relation.units:
                value = relation.data[unit].get(key)
                if value:
                    values.append(value)
        return list(set(values))
