import json
import datetime

from mock import patch

from django.core.urlresolvers import reverse
from seahub.test_utils import BaseTestCase

class SysinfoTest(BaseTestCase):

    def setUp(self):
        self.login_as(self.admin)

    def tearDown(self):
        self.remove_repo()

    @patch('seahub.api2.endpoints.admin.sysinfo.is_pro_version')
    def test_get_sysinfo_in_community_edition(self, mock_is_pro_version):

        mock_is_pro_version.return_value = False

        url = reverse('api-v2.1-sysinfo')
        resp = self.client.get(url)
        json_resp = json.loads(resp.content)

        assert len(json_resp) == 15
        assert json_resp['is_pro'] is False
        assert json_resp['multi_tenancy_enabled'] is False
        assert json_resp['license_maxusers'] == 0

    @patch('seahub.api2.endpoints.admin.sysinfo.is_pro_version')
    @patch('seahub.api2.endpoints.admin.sysinfo.parse_license')
    def test_get_sysinfo_in_pro_edition(self, mock_parse_license, mock_is_pro_version):

        test_user = 'Test user'

        mock_is_pro_version.return_value = True
        mock_parse_license.return_value = {
            'Hash': '2981bd12cf0c83c81aaa453ce249ffdd2e492ed2220f3c89c57f06518de36c487c873be960577a0534f3de4ac2bb52d3918016aaa07d60dccbce92673bc23604f4d8ff547f88287c398f74f16e114a8a3b978cce66961fd0facd283da7b050b5fc6205934420e1b4a65daf1c6dcdb2dc78e38a3799eeb5533779595912f1723129037f093f925d8ab94478c8aded304c62d003c07a6e98e706fdf81b6f73c3a806f523bbff1a92f8eb8ea325e09b2b80acfc4b99dd0f5b339d5ed832da00bad3394b9d40a09cce6066b6dc2c9b2ec47338de41867f5c2380c96f7708a5e9cdf244fbdfa1cc174751b90e74e620f53778593b84ec3b15175c3e432c20dcb4cfde',
            'Name': test_user,
            'Mode': 'life-time',
            'Licencetype': 'User',
            'LicenceKEY': '1461659711',
            'Expiration': '2016-5-6',
            'MaxUsers': '500',
            'ProductID': 'Seafile server'
        }

        url = reverse('api-v2.1-sysinfo')
        resp = self.client.get(url)
        json_resp = json.loads(resp.content)

        assert len(json_resp) == 15
        assert json_resp['license_maxusers'] == 500
        assert json_resp['license_to'] == test_user


class FileOperationsInfoText(BaseTestCase):
    def setUp(self):
        self.login_as(self.admin)

    @patch("seahub.api2.endpoints.admin.sysinfo.get_file_audit_stats")
    @patch("seahub.api2.endpoints.admin.sysinfo.get_file_audit_stats_by_day")
    def test_can_get_file_audit_stats(self, mock_get_file_audit_stats_by_day, mock_get_file_audit_stats):
        mock_get_file_audit_stats.return_value = [
            (datetime.datetime(2017, 6, 2, 7, 0), u'Added', 2L),
            (datetime.datetime(2017, 6, 2, 7, 0), u'Deleted', 2L),
            (datetime.datetime(2017, 6, 2, 7, 0), u'Visited', 2L),
            (datetime.datetime(2017, 6, 2, 8, 0), u'Added', 3L),
            (datetime.datetime(2017, 6, 2, 8, 0), u'Deleted', 4L),
            (datetime.datetime(2017, 6, 2, 8, 0), u'Visited', 5L)]
        mock_get_file_audit_stats_by_day.return_value = [
            (datetime.datetime(2017, 6, 2, 23, 0), u'Added', 2L),
            (datetime.datetime(2017, 6, 2, 23, 0), u'Deleted', 2L),
            (datetime.datetime(2017, 6, 2, 23, 0), u'Visited', 2L),
        ]
        url = reverse('api-v2.1-admin-file-operations')
        url += "?start=2017-06-01 07:00:00&end=2017-06-03 07:00:00&group_by=hour"
        resp = self.client.get(url)
        json_resp = json.loads(resp.content)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(json_resp[0]['datetime'], "2017-06-02 07:00:00")
        self.assertEqual(json_resp[0]['added'], 2)
        self.assertEqual(json_resp[0]['deleted'], 2)
        self.assertEqual(json_resp[0]['visited'], 2)
        self.assertEqual(json_resp[1]['datetime'], "2017-06-02 08:00:00")
        self.assertEqual(json_resp[1]['added'], 3)
        self.assertEqual(json_resp[1]['deleted'], 4)
        self.assertEqual(json_resp[1]['visited'], 5)
        url += "?start=2017-06-01 07:00:00&end=2017-06-03 07:00:00&group_by=day"
        resp = self.client.get(url)
        json_resp = json.loads(resp.content)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(json_resp[0]['datetime'], "2017-06-02 23:00:00")
        self.assertEqual(json_resp[0]['added'], 2)
        self.assertEqual(json_resp[0]['deleted'], 2)
        self.assertEqual(json_resp[0]['visited'], 2)

    @patch("seahub.api2.endpoints.admin.sysinfo.get_user_activity_stats")
    @patch("seahub.api2.endpoints.admin.sysinfo.get_user_activity_stats_by_day")
    def test_can_user_activity_stats(self, mock_stats_by_day, mock_stats):
        mock_stats.return_value = [(datetime.datetime(2017, 6, 2, 7, 0), 2L),
                             (datetime.datetime(2017, 6, 2, 8, 0), 5L)]
        mock_stats_by_day.return_value = [(datetime.datetime(2017, 6, 2, 23, 0), 3L)]
        url = reverse('api-v2.1-admin-active-users')
        url += "?start=2017-06-01 07:00:00&end=2017-06-03 07:00:00&group_by=hour"
        resp = self.client.get(url)
        json_resp = json.loads(resp.content)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(json_resp[0]['datetime'], "2017-06-02 07:00:00")
        self.assertEqual(json_resp[0]['count'], 2)
        self.assertEqual(json_resp[1]['datetime'], "2017-06-02 08:00:00")
        self.assertEqual(json_resp[1]['count'], 5)
        url += "?start=2017-06-01 07:00:00&end=2017-06-03 07:00:00&group_by=day"
        resp = self.client.get(url)
        json_resp = json.loads(resp.content)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(json_resp[0]['datetime'], "2017-06-02 23:00:00")
        self.assertEqual(json_resp[0]['count'], 3)

    @patch("seahub.api2.endpoints.admin.sysinfo.get_total_storage_stats")
    @patch("seahub.api2.endpoints.admin.sysinfo.get_total_storage_stats_by_day")
    def test_can_get_total_storage_stats(self, mock_stats_by_day, mock_stats):
        mock_stats.return_value = [(datetime.datetime(2017, 6, 2, 7, 0), 2L),
                             (datetime.datetime(2017, 6, 2, 8, 0), 5L)]
        mock_stats_by_day.return_value = [(datetime.datetime(2017, 6, 2, 23, 0), 13L)]
        url = reverse('api-v2.1-admin-total-storage')
        url += "?start=2017-06-01 07:00:00&end=2017-06-03 07:00:00&group_by=hour"
        resp = self.client.get(url)
        json_resp = json.loads(resp.content)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(json_resp[0]['datetime'], "2017-06-02 07:00:00")
        self.assertEqual(json_resp[0]['total_storage'], 2)
        self.assertEqual(json_resp[1]['datetime'], "2017-06-02 08:00:00")
        self.assertEqual(json_resp[1]['total_storage'], 5)
        url += "?start=2017-06-01 07:00:00&end=2017-06-03 07:00:00&group_by=day"
        resp = self.client.get(url)
        json_resp = json.loads(resp.content)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(json_resp[0]['datetime'], "2017-06-02 23:00:00")
        self.assertEqual(json_resp[0]['total_storage'], 13)
