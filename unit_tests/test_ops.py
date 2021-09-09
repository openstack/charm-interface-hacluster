#!/usr/bin/env python3

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

import unittest
import sys
sys.path.append('.')  # noqa
from ops.testing import Harness
from ops.charm import CharmBase
import interface_hacluster.ops_ha_interface as ops_ha_interface


class HAServiceRequires(unittest.TestCase):

    class MyCharm(CharmBase):

        def __init__(self, *args):
            super().__init__(*args)
            self.seen_events = []
            self.ha = ops_ha_interface.HAServiceRequires(self, 'ha')

            self.framework.observe(
                self.ha.on.ha_ready,
                self._log_event)

        def _log_event(self, event):
            self.seen_events.append(type(event).__name__)

    def setUp(self):
        super().setUp()
        self.harness = Harness(
            self.MyCharm,
            meta='''
name: my-charm
requires:
  ha:
    interface: hacluster
    scope: container
'''
        )

    def test_local_vars(self):
        self.harness.begin()
        self.harness.charm.ha.set_local('a', 'b')
        self.assertEqual(
            self.harness.charm.ha.get_local('a'),
            'b')
        self.harness.charm.ha.set_local(**{'c': 'd', 'e': 'f'})
        self.assertEqual(
            self.harness.charm.ha.get_local('c'),
            'd')
        self.assertEqual(
            self.harness.charm.ha.get_local('e'),
            'f')
        self.harness.charm.ha.set_local(data={'g': 'h', 'i': 'j'})
        self.assertEqual(
            self.harness.charm.ha.get_local('g'),
            'h')
        self.assertEqual(
            self.harness.charm.ha.get_local('i'),
            'j')

    def test_remote_vars(self):
        self.harness.begin()
        rel_id = self.harness.add_relation(
            'ha',
            'hacluster')
        self.harness.add_relation_unit(
            rel_id,
            'hacluster/0')
        self.harness.charm.ha.set_remote('a', 'b')
        rel_data = self.harness.get_relation_data(
            rel_id,
            'my-charm/0')
        self.assertEqual(rel_data, {'a': 'b'})

    def test_get_remote_all(self):
        self.harness.begin()
        rel_id1 = self.harness.add_relation(
            'ha',
            'hacluster-a')
        self.harness.add_relation_unit(
            rel_id1,
            'hacluster-a/0')
        self.harness.update_relation_data(
            rel_id1,
            'hacluster-a/0',
            {'fruit': 'banana'})
        self.harness.add_relation_unit(
            rel_id1,
            'hacluster-a/1')
        self.harness.update_relation_data(
            rel_id1,
            'hacluster-a/1',
            {'fruit': 'orange'})
        rel_id2 = self.harness.add_relation(
            'ha',
            'hacluster-b')
        self.harness.add_relation_unit(
            rel_id2,
            'hacluster-b/0')
        self.harness.update_relation_data(
            rel_id2,
            'hacluster-b/0',
            {'fruit': 'grape'})
        self.harness.add_relation_unit(
            rel_id2,
            'hacluster-b/1')
        self.harness.update_relation_data(
            rel_id2,
            'hacluster-b/1',
            {'veg': 'carrot'})
        self.assertEqual(
            self.harness.charm.ha.get_remote_all('fruit'),
            ['orange', 'grape', 'banana'])

    def test_ha_ready(self):
        self.harness.begin()
        self.assertEqual(
            self.harness.charm.seen_events,
            [])
        rel_id = self.harness.add_relation(
            'ha',
            'hacluster')
        self.harness.add_relation_unit(
            rel_id,
            'hacluster/0')
        self.harness.update_relation_data(
            rel_id,
            'hacluster/0',
            {'clustered': 'yes'})
        self.assertEqual(
            self.harness.charm.seen_events,
            ['HAServiceReadyEvent'])

    def test_data_changed(self):
        self.harness.begin()
        self.assertTrue(
            self.harness.charm.ha.data_changed(
                'relation-data', {'a': 'b'}))
        self.assertFalse(
            self.harness.charm.ha.data_changed(
                'relation-data', {'a': 'b'}))
        self.assertTrue(
            self.harness.charm.ha.data_changed(
                'relation-data', {'a': 'c'}))
