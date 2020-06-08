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

from unittest import mock
import unittest

import common


class TestHAClusterCommonCRM(unittest.TestCase):

    def test_init(self):
        crm = common.CRM()
        expect = {
            'resources': {},
            'delete_resources': [],
            'resource_params': {},
            'groups': {},
            'ms': {},
            'orders': {},
            'colocations': {},
            'clones': {},
            'locations': {},
            'init_services': [],
            'systemd_services': []}

        self.assertEqual(
            crm,
            expect)

        expect['resources'] = {'res1': 'res1'}
        self.assertEqual(
            common.CRM(resources={'res1': 'res1'}),
            expect)
        self.assertEqual(
            common.CRM({'resources': {'res1': 'res1'}}),
            expect)

    def test_primitive(self):
        crm = common.CRM()
        crm.primitive('www8', 'apache',
                      params='configfile=/etc/apache/www8.conf',
                      operations='$id-ref=apache_ops')
        self.assertEqual(
            crm['resources']['www8'],
            'apache')
        self.assertEqual(
            crm['resource_params']['www8'],
            ('  params configfile=/etc/apache/www8.conf  '
             'operations $id-ref=apache_ops'))

    def test_primitive_description(self):
        crm = common.CRM()
        crm.primitive('www8', 'apache',
                      description='super awesome',
                      params='configfile=/etc/apache/www8.conf',
                      operations='$id-ref=apache_ops')
        self.assertEqual(
            crm['resources']['www8'],
            'apache')
        self.assertEqual(
            crm['resource_params']['www8'],
            ('description="super awesome"'
             '  params configfile=/etc/apache/www8.conf  '
             'operations $id-ref=apache_ops'))

    def test_primitive_multiops(self):
        crm = common.CRM()
        ops = ['monitor role=Master interval=60s',
               'monitor role=Slave interval=300s']

        crm.primitive('r0', 'ocf:linbit:drbd',
                      params='drbd_resource=r0',
                      op=ops)
        self.assertEqual(
            crm['resources']['r0'],
            'ocf:linbit:drbd')
        self.assertEqual(
            crm['resource_params']['r0'],
            ('  params drbd_resource=r0  op monitor role=Master '
             'interval=60s op monitor role=Slave interval=300s'))

    def test__parse(self):
        crm = common.CRM()
        self.assertEqual(
            crm._parse('prefix', 'var1'),
            ' prefix var1')
        self.assertEqual(
            crm._parse('prefix', ['var1']),
            ' prefix var1')
        self.assertEqual(
            crm._parse('prefix', ['var1', 'var2']),
            ' prefix var1 prefix var2')

    def test_clone(self):
        crm = common.CRM()
        crm.clone(
            'cl_nova_haproxy',
            'res_neutron_haproxy',
            description='FE Haproxy')
        self.assertEqual(
            crm['clones']['cl_nova_haproxy'],
            'res_neutron_haproxy description="FE Haproxy"')

    def test_clone_meta(self):
        crm = common.CRM()
        crm.clone(
            'cl_nova_haproxy',
            'res_neutron_haproxy',
            description='FE Haproxy',
            meta='clone-node-max=1')
        self.assertEqual(
            crm['clones']['cl_nova_haproxy'],
            ('res_neutron_haproxy description="FE Haproxy"  '
             'meta clone-node-max=1'))

    def test_colocation(self):
        crm = common.CRM()
        crm.colocation('console_with_vip', 'ALWAYS', 'nova-console', 'vip')
        self.assertEqual(
            crm['colocations']['console_with_vip'],
            'ALWAYS: nova-console vip')

    def test_colocation_node_attr(self):
        crm = common.CRM()
        crm.colocation(
            'console_with_vip',
            'ALWAYS',
            'nova-console',
            'vip',
            node_attribute='attr1')
        self.assertEqual(
            crm['colocations']['console_with_vip'],
            'ALWAYS: nova-console vip node-attribute=attr1')

    def test_group(self):
        crm = common.CRM()
        crm.group('grp_mysql', 'res_mysql_rbd', 'res_mysql_fs',
                  'res_mysql_vip', 'res_mysqld')
        self.assertEqual(
            crm['groups']['grp_mysql'],
            'res_mysql_rbd res_mysql_fs res_mysql_vip res_mysqld')

    def test_group_meta(self):
        crm = common.CRM()
        crm.group('grp_mysql', 'res_mysql_rbd', 'res_mysql_fs',
                  'res_mysql_vip', 'res_mysqld', meta='container="vm"')
        self.assertEqual(
            crm['groups']['grp_mysql'],
            ('res_mysql_rbd res_mysql_fs res_mysql_vip res_mysqld  '
             'meta container="vm"'))

    def test_group_meta_and_params(self):
        crm = common.CRM()
        crm.group('grp_mysql', 'res_mysql_rbd', 'res_mysql_fs',
                  'res_mysql_vip', 'res_mysqld', meta='container="vm"',
                  params='config=/etc/mysql/db0.conf')
        self.assertEqual(
            crm['groups']['grp_mysql'],
            ('res_mysql_rbd res_mysql_fs res_mysql_vip res_mysqld  '
             'meta container="vm"  '
             'params config=/etc/mysql/db0.conf'))

    def test_group_desc(self):
        crm = common.CRM()
        crm.group('grp_mysql', 'res_mysql_rbd', 'res_mysql_fs',
                  'res_mysql_vip', 'res_mysqld', description='useful desc')
        self.assertEqual(
            crm['groups']['grp_mysql'],
            ('res_mysql_rbd res_mysql_fs res_mysql_vip res_mysqld '
             'description=useful desc"'))

    def test_delete_resource(self):
        crm = common.CRM()
        crm.delete_resource('res_mysql_vip')
        self.assertEqual(
            crm['delete_resources'],
            ('res_mysql_vip',))

    def test_delete_resource_multi(self):
        crm = common.CRM()
        crm.delete_resource('res_mysql_vip', 'grp_mysql')
        self.assertEqual(
            crm['delete_resources'],
            ('res_mysql_vip', 'grp_mysql'))

    def test_add_delete_resource(self):
        crm = common.CRM()
        crm.add_delete_resource('res_mysql_vip')
        self.assertEqual(crm['delete_resources'], ('res_mysql_vip',))

    def test_add_delete_resource_multi(self):
        crm = common.CRM()
        crm.add_delete_resource('res_mysql_vip')
        crm.add_delete_resource('grp_mysql')
        self.assertEqual(
            crm['delete_resources'],
            ('res_mysql_vip', 'grp_mysql'))

    def test_add_delete_resource_mix(self):
        crm = common.CRM()
        crm.delete_resource('grp_mysql')
        crm.add_delete_resource('res_mysql_vip')
        self.assertEqual(
            crm['delete_resources'],
            ('grp_mysql', 'res_mysql_vip'))

    def test_add_delete_resource_dupe(self):
        crm = common.CRM()
        crm.add_delete_resource('res_mysql_vip')
        crm.add_delete_resource('res_mysql_vip')
        self.assertEqual(
            crm['delete_resources'],
            ('res_mysql_vip',))

    def test_init_services(self):
        crm = common.CRM()
        crm.init_services('haproxy')
        self.assertEqual(
            crm['init_services'],
            ('haproxy',))

    def test_init_services_multi(self):
        crm = common.CRM()
        crm.init_services('haproxy', 'apache2')
        self.assertEqual(
            crm['init_services'],
            ('haproxy', 'apache2'))

    def test_ms_meta(self):
        crm = common.CRM()
        crm.ms('disk1', 'drbd1', meta='notify=true globally-unique=false')
        self.assertEqual(
            crm['ms']['disk1'],
            'drbd1  meta notify=true globally-unique=false')

    def test_ms_meta_and_params(self):
        crm = common.CRM()
        crm.ms('disk1', 'drbd1',
               meta='notify=true globally-unique=false',
               params='config=/etc/mysql/db0.conf')
        self.assertEqual(
            crm['ms']['disk1'],
            'drbd1  meta notify=true globally-unique=false  '
            'params config=/etc/mysql/db0.conf')

    def test_ms_desc(self):
        crm = common.CRM()
        crm.ms('disk1', 'drbd1', description='useful desc')
        self.assertEqual(
            crm['ms']['disk1'],
            'drbd1 description="useful desc"')

    def test_systemd_services(self):
        crm = common.CRM()
        crm.systemd_services('haproxy')
        self.assertEqual(
            crm['systemd_services'],
            ('haproxy',))

    def test_systemd_services_multi(self):
        crm = common.CRM()
        crm.systemd_services('haproxy', 'apache2')
        self.assertEqual(
            crm['systemd_services'],
            ('haproxy', 'apache2'))

    # The method signature of 'order' seems broken. Leaving out unit tests for
    # it as they would just confirm broken behaviour.

    def test_add(self):
        crm = common.CRM()
        mock1 = mock.MagicMock()
        mock2 = mock.MagicMock()
        mock1.configure_resource = mock2
        crm.add(mock1)
        mock2.assert_called_once_with(crm)


class TestHAClusterCommonInitService(unittest.TestCase):

    def test_init(self):
        init_svc = common.InitService('apache', 'apache2')
        self.assertEqual(
            init_svc.service_name,
            'apache')
        self.assertEqual(
            init_svc.init_service_name,
            'apache2')
        self.assertTrue(init_svc.clone)

    def test_init_no_clone(self):
        init_svc = common.InitService('apache', 'apache2', clone=False)
        self.assertFalse(init_svc.clone)

    def test_configure_resource(self):
        crm = common.CRM()
        init_svc = common.InitService('apache', 'apache2')
        init_svc.configure_resource(crm)
        self.assertEqual(
            crm['resources']['res_apache_apache2'],
            'lsb:apache2')
        self.assertEqual(
            crm['resource_params']['res_apache_apache2'],
            ('  meta migration-threshold="INFINITY" failure-timeout="5s"'
             '  op monitor interval="5s"'))
        self.assertEqual(crm['init_services'], ('apache2',))
        self.assertEqual(
            crm['clones']['cl_res_apache_apache2'],
            'res_apache_apache2')

    def test_configure_resource_no_clone(self):
        crm = common.CRM()
        init_svc = common.InitService('apache', 'apache2', clone=False)
        init_svc.configure_resource(crm)
        self.assertEqual(
            crm['resources']['res_apache_apache2'],
            'lsb:apache2')
        self.assertEqual(
            crm['resource_params']['res_apache_apache2'],
            ('  meta migration-threshold="INFINITY" failure-timeout="5s"'
             '  op monitor interval="5s"'))
        self.assertEqual(crm['init_services'], ('apache2',))
        self.assertFalse(crm['clones'].get('cl_res_apache_apache2'))


class TestHAClusterCommonVirtualIP(unittest.TestCase):

    def test_init(self):
        vip_svc = common.VirtualIP('apache', '10.110.1.1')
        self.assertEqual(vip_svc.service_name, 'apache')
        self.assertEqual(vip_svc.vip, '10.110.1.1')
        self.assertIsNone(vip_svc.nic)
        self.assertIsNone(vip_svc.cidr)

    def test_init_no_default(self):
        vip_svc = common.VirtualIP('apache', '10.110.1.1', 'eth1', '24')
        self.assertEqual(vip_svc.service_name, 'apache')
        self.assertEqual(vip_svc.vip, '10.110.1.1')
        self.assertEqual(vip_svc.nic, 'eth1')
        self.assertEqual(vip_svc.cidr, '24')

    def test_configure_resource(self):
        crm = common.CRM()
        vip_svc = common.VirtualIP('apache', '10.110.1.1', 'eth1', '24')
        vip_svc.configure_resource(crm)
        self.assertEqual(
            crm['resources']['res_apache_eth1_vip'],
            'ocf:heartbeat:IPaddr2')
        self.assertEqual(
            crm['resource_params']['res_apache_eth1_vip'],
            ('  params ip="10.110.1.1" nic="eth1" cidr_netmask="24"  '
             'meta migration-threshold="INFINITY" failure-timeout="5s"  '
             'op monitor timeout="20s" interval="10s" depth="0"'))

    def test_configure_resource_no_nic(self):
        crm = common.CRM()
        vip_svc = common.VirtualIP('apache', '10.110.1.1')
        vip_svc.configure_resource(crm)
        self.assertEqual(
            crm['resources']['res_apache_a7815c8_vip'],
            'ocf:heartbeat:IPaddr2')
        self.assertEqual(
            crm['resource_params']['res_apache_a7815c8_vip'],
            ('  params ip="10.110.1.1"  '
             'meta migration-threshold="INFINITY" failure-timeout="5s"  '
             'op monitor timeout="20s" interval="10s" depth="0"'))


class TestHAClusterCommonDNSEntry(unittest.TestCase):

    def test_init(self):
        dns_svc = common.DNSEntry(
            'keystone',
            '10.110.1.1',
            'keystone.admin',
            'admin')
        self.assertEqual(dns_svc.service_name, 'keystone')
        self.assertEqual(dns_svc.ip, '10.110.1.1')
        self.assertEqual(dns_svc.fqdn, 'keystone.admin')
        self.assertEqual(dns_svc.endpoint_type, 'admin')

    def test_configure_resource(self):
        crm = common.CRM()
        dns_svc = common.DNSEntry(
            'keystone',
            '10.110.1.1',
            'keystone.admin',
            'admin')
        dns_svc.configure_resource(crm)
        self.assertEqual(
            crm['resources']['res_keystone_admin_hostname'],
            'ocf:maas:dns')
        self.assertEqual(
            crm['resource_params']['res_keystone_admin_hostname'],
            '  params  fqdn="keystone.admin" ip_address="10.110.1.1"')


class TestHAClusterCommonSystemdService(unittest.TestCase):

    def test_systemd(self):
        systemd_svc = common.SystemdService('apache', 'apache2')
        self.assertEqual(
            systemd_svc.service_name,
            'apache')
        self.assertEqual(
            systemd_svc.systemd_service_name,
            'apache2')
        self.assertTrue(systemd_svc.clone)

    def test_systemd_no_clone(self):
        systemd_svc = common.SystemdService('apache', 'apache2', clone=False)
        self.assertFalse(systemd_svc.clone)

    def test_configure_resource(self):
        crm = common.CRM()
        systemd_svc = common.SystemdService('apache', 'apache2')
        systemd_svc.configure_resource(crm)
        self.assertEqual(
            crm['resources']['res_apache_apache2'],
            'systemd:apache2')
        self.assertEqual(
            crm['resource_params']['res_apache_apache2'],
            ('  meta migration-threshold="INFINITY" failure-timeout="5s"'
             '  op monitor interval="5s"'))
        self.assertEqual(crm['systemd_services'], ('apache2',))
        self.assertEqual(
            crm['clones']['cl_res_apache_apache2'],
            'res_apache_apache2')

    def test_configure_resource_no_clone(self):
        crm = common.CRM()
        systemd_svc = common.SystemdService('apache', 'apache2', clone=False)
        systemd_svc.configure_resource(crm)
        self.assertEqual(
            crm['resources']['res_apache_apache2'],
            'systemd:apache2')
        self.assertEqual(
            crm['resource_params']['res_apache_apache2'],
            ('  meta migration-threshold="INFINITY" failure-timeout="5s"'
             '  op monitor interval="5s"'))
        self.assertEqual(crm['systemd_services'], ('apache2',))
        self.assertFalse(crm['clones'].get('cl_res_apache_apache2'))
