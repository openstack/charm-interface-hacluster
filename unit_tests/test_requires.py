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


import json
import mock
import unittest

import common

# Deal with the 'relations.hacluster.common' import in requires.py which
# is invalid in the unit tests as there is no 'relations'.
relations_mock = mock.MagicMock()
relations_mock.hacluster.common = common
modules = {
    'relations': relations_mock,
    'relations.hacluster': mock.MagicMock(),
    'relations.hacluster.common': common,
}
module_patcher = mock.patch.dict('sys.modules', modules)
module_patcher.start()

with mock.patch('charmhelpers.core.hookenv.metadata') as _meta:
    _meta.return_Value = 'ss'
    import requires

_hook_args = {}

TO_PATCH = [
    'data_changed',
]


def mock_hook(*args, **kwargs):

    def inner(f):
        # remember what we were passed.  Note that we can't actually determine
        # the class we're attached to, as the decorator only gets the function.
        _hook_args[f.__name__] = dict(args=args, kwargs=kwargs)
        return f
    return inner


class TestHAClusterRequires(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._patched_hook = mock.patch('charms.reactive.when', mock_hook)
        cls._patched_hook_started = cls._patched_hook.start()
        # force requires to rerun the mock_hook decorator:
        # try except is Python2/Python3 compatibility as Python3 has moved
        # reload to importlib.
        try:
            reload(requires)
        except NameError:
            import importlib
            importlib.reload(requires)

    @classmethod
    def tearDownClass(cls):
        cls._patched_hook.stop()
        cls._patched_hook_started = None
        cls._patched_hook = None
        # and fix any breakage we did to the module
        try:
            reload(requires)
        except NameError:
            import importlib
            importlib.reload(requires)

    def patch(self, method):
        _m = mock.patch.object(self.obj, method)
        _mock = _m.start()
        self.addCleanup(_m.stop)
        return _mock

    def setUp(self):
        self.cr = requires.HAClusterRequires('some-relation', [])
        self.reactive_db = {}
        self._patches = {}
        self._patches_start = {}
        self.obj = requires
        for method in TO_PATCH:
            setattr(self, method, self.patch(method))

    def tearDown(self):
        self.cr = None
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def _set_local(self, key=None, value=None, **kwdata):
        if key is not None:
            self.reactive_db[key] = value
        self.reactive_db.update(kwdata)

    def _get_db_res(self, key):
        return self.reactive_db['resources'][key]

    def _get_local(self, key):
        return self.reactive_db.get(key)

    def mock_reactive_db(self, preseed=None):
        self.patch_kr('get_local')
        self.get_local.side_effect = self._get_local
        self.patch_kr('set_local')
        self.set_local.side_effect = self._set_local
        if preseed:
            self._set_local(resources=preseed)

    def patch_kr(self, attr, return_value=None):
        mocked = mock.patch.object(self.cr, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)

    def test_joined(self):
        self.patch_kr('set_state')
        self.cr.joined()
        self.set_state.assert_called_once_with('{relation_name}.connected')

    def test_changed(self):
        self.patch_kr('is_clustered', True)
        self.patch_kr('set_state')
        self.cr.changed()
        self.set_state.assert_called_once_with('{relation_name}.available')

    def test_changed_not_clustered(self):
        self.patch_kr('is_clustered', False)
        self.patch_kr('remove_state')
        self.cr.changed()
        self.remove_state.assert_called_once_with('{relation_name}.available')

    def test_departed(self):
        self.patch_kr('remove_state')
        self.cr.departed()
        self.remove_state.assert_has_calls([
            mock.call('{relation_name}.available'),
            mock.call('{relation_name}.connected')])

    def test_is_clustered(self):
        self.patch_kr('get_remote_all')

        self.get_remote_all.return_value = [True]
        self.assertTrue(self.cr.is_clustered())

        self.get_remote_all.return_value = ['true']
        self.assertTrue(self.cr.is_clustered())

        self.get_remote_all.return_value = ['yes']
        self.assertTrue(self.cr.is_clustered())

        self.get_remote_all.return_value = None
        self.assertFalse(self.cr.is_clustered())

        self.get_remote_all.return_value = [False]
        self.assertFalse(self.cr.is_clustered())

        self.get_remote_all.return_value = ['false']
        self.assertFalse(self.cr.is_clustered())

        self.get_remote_all.return_value = ['flump']
        self.assertFalse(self.cr.is_clustered())

    def jsonify(self, options):
        json_encode_options = dict(
            sort_keys=True,
        )
        for k, v in options.items():
            if v:
                options[k] = json.dumps(v, **json_encode_options)

    def test_manage_resources(self):
        res = common.CRM()
        res.primitive('res_neutron_haproxy', 'lsb:haproxy',
                      op='monitor interval="5s"')
        res.init_services('haproxy')
        res.clone('cl_nova_haproxy', 'res_neutron_haproxy')
        expected = {
            'json_clones': {"cl_nova_haproxy": "res_neutron_haproxy"},
            'json_init_services': ["haproxy"],
            'json_resource_params': {
                "res_neutron_haproxy": '  op monitor interval="5s"'},
            'json_resources': {"res_neutron_haproxy": "lsb:haproxy"}}
        self.jsonify(expected)
        self.data_changed.return_value = True
        self.patch_kr('set_local')
        self.patch_kr('set_remote')
        self.cr.manage_resources(res)
        self.set_local.assert_called_once_with(**expected)
        self.set_remote.assert_called_once_with(**expected)

    def test_manage_resources_no_change(self):
        res = common.CRM()
        res.primitive('res_neutron_haproxy', 'lsb:haproxy',
                      op='monitor interval="5s"')
        res.init_services('haproxy')
        res.clone('cl_nova_haproxy', 'res_neutron_haproxy')
        self.data_changed.return_value = False
        self.patch_kr('set_local')
        self.patch_kr('set_remote')
        self.cr.manage_resources(res)
        self.assertFalse(self.set_local.called)
        self.assertFalse(self.set_remote.called)

    def test_bind_resources(self):
        expected = {
            'colocations': {}, 'groups': {},
            'clones': {}, 'orders': {},
            'resource_params': {}, 'delete_resources': [],
            'init_services': [], 'locations': {},
            'some': 'resources', 'systemd_services': [],
            'resources': {}, 'ms': {}
        }
        self.patch_kr('get_local', expected)
        self.patch_kr('bind_on')
        self.patch_kr('manage_resources')
        self.cr.bind_resources()
        self.bind_on.assert_called_once_with(iface=None, mcastport=4440)
        self.manage_resources.assert_called_once_with(expected)

    def test_bind_resources_no_defaults(self):
        expected = {
            'colocations': {}, 'groups': {},
            'clones': {}, 'orders': {},
            'resource_params': {}, 'delete_resources': [],
            'init_services': [], 'locations': {},
            'some': 'resources', 'systemd_services': [],
            'resources': {}, 'ms': {}
        }
        self.patch_kr('get_local', expected)
        self.patch_kr('bind_on')
        self.patch_kr('manage_resources')
        self.cr.bind_resources(iface='tr34', mcastport=111)
        self.bind_on.assert_called_once_with(iface='tr34', mcastport=111)
        self.manage_resources.assert_called_once_with(expected)

    def test_delete_resource(self):
        existing_data = {
            'resources': {
                'res_mysql_ens3_vip': 'ocf:heartbeat:IPaddr2'},
            'resource_params': {
                'res_mysql_ens3_vip': (
                    '  params ip="10.110.5.43"  op monitor depth="0" '
                    'timeout="20s" interval="10s"')},
            'groups': {},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {},
            'locations': {},
            'init_services': [],
            'systemd_services': []}
        self.mock_reactive_db(existing_data)
        self.cr.delete_resource('res_mysql_ens3_vip')
        self.assertEqual(
            self._get_local('resources')['delete_resources'],
            ('res_mysql_ens3_vip',))
        self.assertIsNone(
            self._get_db_res('resources').get('res_mysql_ens3_vip'))
        self.assertIsNone(
            self._get_db_res('resource_params').get('res_mysql_ens3_vip'))

    def test_delete_resource_multi(self):
        existing_data = {
            'resources': {
                'res_mysql_ens3_vip': 'ocf:heartbeat:IPaddr2',
                'res_mysql_ens4_vip': 'ocf:heartbeat:IPaddr2'},
            'resource_params': {
                'res_mysql_ens3_vip': (
                    '  params ip="10.110.5.43"  op monitor depth="0" '
                    'timeout="20s" interval="10s"'),
                'res_mysql_ens4_vip': (
                    '  params ip="10.110.5.43"  op monitor depth="0" '
                    'timeout="20s" interval="10s"')},
            'groups': {},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {},
            'locations': {},
            'init_services': ('telnetd',),
            'systemd_services': []}
        self.mock_reactive_db(existing_data)
        self.cr.delete_resource('res_mysql_ens3_vip')
        self.cr.delete_resource('res_mysql_ens4_vip')
        self.cr.delete_resource('telnetd')
        self.assertEqual(
            self._get_local('resources')['delete_resources'],
            ('res_mysql_ens3_vip', 'res_mysql_ens4_vip', 'telnetd'))
        self.assertIsNone(
            self._get_db_res('resources').get('res_mysql_ens3_vip'))
        self.assertIsNone(
            self._get_db_res('resource_params').get('res_mysql_ens3_vip'))
        self.assertIsNone(
            self._get_db_res('resources').get('res_mysql_ens4_vip'))
        self.assertIsNone(
            self._get_db_res('resource_params').get('res_mysql_ens4_vip'))
        self.assertFalse(
            'telnetd' in self._get_db_res('init_services'))

    def test_add_vip(self):
        expected = {
            'resources': {
                'res_mysql_4b8ce37_vip': 'ocf:heartbeat:IPaddr2'},
            'delete_resources': [],
            'resource_params': {
                'res_mysql_4b8ce37_vip': (
                    '  params ip="10.110.5.43"'
                    '  meta migration-threshold="INFINITY" '
                    'failure-timeout="5s"'
                    '  op monitor depth="0" '
                    'timeout="20s" interval="10s"')},
            'groups': {},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {},
            'locations': {},
            'init_services': [],
            'systemd_services': []}

        self.mock_reactive_db()
        self.cr.add_vip('mysql', '10.110.5.43')
        self.set_local.assert_called_once_with(resources=expected)

    def test_add_additional_vip(self):
        existing_resource = {
            'resources': {
                'res_mysql_4b8ce37_vip': 'ocf:heartbeat:IPaddr2'},
            'delete_resources': [],
            'resource_params': {
                'res_mysql_4b8ce37_vip': (
                    '  params ip="10.110.5.43"  op monitor depth="0" '
                    'timeout="20s" interval="10s"')},
            'groups': {},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {},
            'locations': {},
            'init_services': [],
            'systemd_services': []}

        expected = {
            'resources': {
                'res_mysql_4b8ce37_vip': 'ocf:heartbeat:IPaddr2',
                'res_mysql_1993276_vip': 'ocf:heartbeat:IPaddr2'},
            'delete_resources': [],
            'resource_params': {
                'res_mysql_4b8ce37_vip': (
                    '  params ip="10.110.5.43"'
                    '  op monitor depth="0" '
                    'timeout="20s" interval="10s"'),
                'res_mysql_1993276_vip': (
                    '  params ip="10.120.5.43"'
                    '  meta migration-threshold="INFINITY" '
                    'failure-timeout="5s"'
                    '  op monitor depth="0" '
                    'timeout="20s" interval="10s"')},
            'groups': {
                'grp_mysql_vips': ('res_mysql_1993276_vip '
                                   'res_mysql_4b8ce37_vip')},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {},
            'locations': {},
            'init_services': [],
            'systemd_services': []}

        self.mock_reactive_db(existing_resource)
        self.cr.add_vip('mysql', '10.120.5.43')
        self.set_local.assert_called_once_with(resources=expected)

    def test_add_init_service(self):
        expected = {
            'resources': {
                'res_mysql_telnetd': 'lsb:telnetd'},
            'delete_resources': [],
            'resource_params': {
                'res_mysql_telnetd':
                    ('  meta migration-threshold="INFINITY" '
                     'failure-timeout="5s"'
                     '  op monitor interval="5s"')},
            'groups': {},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {'cl_res_mysql_telnetd': 'res_mysql_telnetd'},
            'locations': {},
            'init_services': ('telnetd',),
            'systemd_services': []}
        self.mock_reactive_db()
        self.cr.add_init_service('mysql', 'telnetd')
        self.set_local.assert_called_once_with(resources=expected)

    def test_add_dnsha(self):
        expected = {
            'resources': {
                'res_keystone_public_hostname': 'ocf:maas:dns'},
            'delete_resources': [],
            'resource_params': {
                'res_keystone_public_hostname': (
                    '  params  fqdn="keystone.public" '
                    'ip_address="10.110.5.43"')},
            'groups': {},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {},
            'locations': {},
            'init_services': [],
            'systemd_services': []}

        self.mock_reactive_db()
        self.cr.add_dnsha(
            'keystone',
            '10.110.5.43',
            'keystone.public',
            'public')
        self.set_local.assert_called_once_with(resources=expected)

    def test_add_additional_dnsha(self):
        existing_resource = {
            'resources': {
                'res_keystone_public_hostname': 'ocf:maas:dns'},
            'delete_resources': [],
            'resource_params': {
                'res_keystone_public_hostname': (
                    '  params  fqdn="keystone.public" '
                    'ip_address="10.110.5.43"')},
            'groups': {},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {},
            'locations': {},
            'init_services': [],
            'systemd_services': []}
        expected = {
            'resources': {
                'res_keystone_public_hostname': 'ocf:maas:dns',
                'res_keystone_admin_hostname': 'ocf:maas:dns'},
            'delete_resources': [],
            'resource_params': {
                'res_keystone_public_hostname': (
                    '  params  fqdn="keystone.public" '
                    'ip_address="10.110.5.43"'),
                'res_keystone_admin_hostname': (
                    '  params  fqdn="keystone.admin" '
                    'ip_address="10.120.5.43"')},
            'groups': {
                'grp_keystone_hostnames': ('res_keystone_admin_hostname '
                                           'res_keystone_public_hostname')},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {},
            'locations': {},
            'init_services': [],
            'systemd_services': []}

        self.mock_reactive_db(existing_resource)
        self.cr.add_dnsha(
            'keystone',
            '10.120.5.43',
            'keystone.admin',
            'admin')
        self.set_local.assert_called_once_with(resources=expected)

    @mock.patch.object(requires.hookenv, 'related_units')
    @mock.patch.object(requires.hookenv, 'relation_get')
    def test_get_remote_all(self, relation_get, related_units):
        unit_data = {
            'rid:1': {
                'app1/0': {
                    'key1': 'value1',
                    'key2': 'value2'},
                'app1/1': {
                    'key1': 'value1',
                    'key2': 'value3'}},
            'rid:2': {
                'app2/0': {
                    'key1': 'value1',
                    'key2': 'value3'}},
            'rid:3': {},
            'systemd_services': []}

        def get_unit_data(key, unit, relation_id):
            return unit_data[relation_id].get(unit, {}).get(key, {})
        conv1 = mock.MagicMock()
        conv1.relation_ids = ['rid:1', 'rid:2']
        conv2 = mock.MagicMock()
        conv2.relation_ids = ['rid:3']
        self.patch_kr('conversations', [conv1, conv2])
        related_units.side_effect = lambda x: unit_data[x].keys()
        relation_get.side_effect = get_unit_data
        # Check de-duplication:
        self.assertEqual(
            self.cr.get_remote_all('key1'),
            ['value1'])
        # Check multiple values:
        self.assertEqual(
            self.cr.get_remote_all('key2'),
            ['value2', 'value3'])
        # Check missing key
        self.assertEqual(
            self.cr.get_remote_all('key100'),
            [])
        # Check missing key with default
        self.assertEqual(
            self.cr.get_remote_all('key100', default='defaultvalue'),
            ['defaultvalue'])

    def test_add_systemd_service(self):
        expected = {
            'resources': {
                'res_mysql_telnetd': 'systemd:telnetd'},
            'delete_resources': [],
            'resource_params': {
                'res_mysql_telnetd':
                    ('  meta migration-threshold="INFINITY" '
                     'failure-timeout="5s"'
                     '  op monitor interval="5s"')},
            'groups': {},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {'cl_res_mysql_telnetd': 'res_mysql_telnetd'},
            'locations': {},
            'init_services': [],
            'systemd_services': ('telnetd',)}
        self.mock_reactive_db()
        self.cr.add_systemd_service('mysql', 'telnetd')
        self.set_local.assert_called_once_with(resources=expected)
