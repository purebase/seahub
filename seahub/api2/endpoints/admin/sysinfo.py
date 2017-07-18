# Copyright (c) 2012-2016 Seafile Ltd.
import time
import datetime
import logging

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from django.utils.translation import ugettext as _
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from seaserv import seafile_api, ccnet_api
from pysearpc import SearpcError

from seahub.utils import is_pro_version
from seahub.utils import get_file_audit_stats, get_file_audit_stats_by_day,\
        get_total_storage_stats, get_total_storage_stats_by_day,\
        get_user_activity_stats, get_user_activity_stats_by_day
from seahub.utils.licenseparse import parse_license

from seahub.api2.authentication import TokenAuthentication
from seahub.api2.throttling import UserRateThrottle
from seahub.api2.models import TokenV2
from seahub.api2.utils import api_error

try:
    from seahub.settings import MULTI_TENANCY
except ImportError:
    MULTI_TENANCY = False

logger = logging.getLogger(__name__)


class SysInfo(APIView):
    """Show system info.
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    throttle_classes = (UserRateThrottle,)
    permission_classes = (IsAdminUser,)

    def get(self, request, format=None):
        # count repos
        try:
            repos_count = seafile_api.count_repos()
        except SearpcError as e:
            logger.error(e)
            repos_count = 0

        # count groups
        try:
            groups_count = len(ccnet_api.get_all_groups(-1, -1))
        except Exception as e:
            logger.error(e)
            groups_count = 0

        # count orgs
        if MULTI_TENANCY:
            multi_tenancy_enabled = True
            try:
                org_count = ccnet_api.count_orgs()
            except Exception as e:
                logger.error(e)
                org_count = 0
        else:
            multi_tenancy_enabled = False
            org_count = 0

        # count users
        try:
            active_db_users = ccnet_api.count_emailusers('DB')
        except Exception as e:
            logger.error(e)
            active_db_users = 0

        try:
            active_ldap_users = ccnet_api.count_emailusers('LDAP')
        except Exception as e:
            logger.error(e)
            active_ldap_users = 0

        try:
            inactive_db_users = ccnet_api.count_inactive_emailusers('DB')
        except Exception as e:
            logger.error(e)
            inactive_db_users = 0

        try:
            inactive_ldap_users = ccnet_api.count_inactive_emailusers('LDAP')
        except Exception as e:
            logger.error(e)
            inactive_ldap_users = 0

        active_users = active_db_users + active_ldap_users if \
            active_ldap_users > 0 else active_db_users

        inactive_users = inactive_db_users + inactive_ldap_users if\
            inactive_ldap_users > 0 else inactive_db_users

        # get license info
        is_pro = is_pro_version()
        if is_pro:
            license_dict = parse_license()
        else:
            license_dict = {}

        if license_dict:
            with_license = True
            try:
                max_users = int(license_dict.get('MaxUsers', 3))
            except ValueError as e:
                logger.error(e)
                max_users = 0
        else:
            with_license = False
            max_users = 0

        # count total file number
        try:
            total_files_count = seafile_api.get_total_file_number()
        except Exception as e:
            logger.error(e)
            total_files_count = 0

        # count total storage
        try:
            total_storage = seafile_api.get_total_storage()
        except Exception as e:
            logger.error(e)
            total_storage = 0

        # count devices number
        try:
            total_devices_count = TokenV2.objects.get_total_devices_count()
        except Exception as e:
            logger.error(e)
            total_devices_count = 0

        # count current connected devices
        try:
            current_connected_devices_count = TokenV2.objects.\
                    get_current_connected_devices_count()
        except Exception as e:
            logger.error(e)
            current_connected_devices_count = 0

        info = {
            'users_count': active_users + inactive_users,
            'active_users_count': active_users,
            'repos_count': repos_count,
            'total_files_count': total_files_count,
            'groups_count': groups_count,
            'org_count': org_count,
            'multi_tenancy_enabled': multi_tenancy_enabled,
            'is_pro': is_pro,
            'with_license': with_license,
            'license_expiration': license_dict.get('Expiration', ''),
            'license_maxusers': max_users,
            'license_to': license_dict.get('Name', ''),
            'total_storage': total_storage,
            'total_devices_count': total_devices_count,
            'current_connected_devices_count': current_connected_devices_count,
        }

        return Response(info)


def check_parameter(func):
    def _decorated(view, request, *args, **kwargs):
        start_time = request.GET.get("start", "")
        end_time = request.GET.get("end", "")
        group_by = request.GET.get("group_by", "hour")
        if not start_time:
            error_msg = _("Start time can not be empty")
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        if not end_time:
            error_msg = _("End time can not be empty")
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        if group_by.lower() not in ["hour", "day"]:
            error_msg = "Record only can group by day or hour"
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        try:
            start_time = datetime.datetime.strptime(start_time,
                                                    "%Y-%m-%d %H:%M:%S")
        except:
            error_msg = _("Start time %s invalid") % start_time
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)
        try:
            end_time = datetime.datetime.strptime(end_time,
                                                  "%Y-%m-%d %H:%M:%S")
        except:
            error_msg = _("End time %s invalid") % end_time
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        return func(view, request, start_time, end_time, group_by)
    return _decorated


class FileOperationsView(APIView):
    """
    The  File Operations Record .
        Permission checking:
        1. only admin can perform this action.
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    throttle_classes = (UserRateThrottle,)
    permission_classes = (IsAdminUser,)

    @check_parameter
    def get(self, request, start_time, end_time, group_by):
        """
        Get a record of the specifiy time
            param:
                start: the start time of the query.
                end: the end time of the query.
                group_by:decide the record group by day or hour,default group by hour.
            return:
                the list of file operations record.
        """
        if group_by == "hour":
            data = get_file_audit_stats(start_time, end_time)
        elif group_by == "day":
            data = get_file_audit_stats_by_day(start_time, end_time)

        res_data = []
        dict_data = {}
        for i in data:
            timestamp = str(int(time.mktime(i[0].timetuple())))
            if dict_data.get(timestamp, None) is None:
                dict_data[timestamp] = {}
            dict_data[timestamp][i[1]] = i[2]
        for x, y in dict_data.items():
            timeArray = time.localtime(int(x))
            x = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
            added = y.get('Added', '0')
            deleted = y.get('Deleted', '0')
            visited = y.get('Visited', '0')
            res_data.append(dict(zip(['datetime', 'added', 'deleted',
                                      'visited'], [x, added, deleted,
                                                   visited])))
        return Response(sorted(res_data, key=lambda x: x['datetime']))


class TotalStorageView(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    throttle_classes = (UserRateThrottle,)
    permission_classes = (IsAdminUser,)

    @check_parameter
    def get(self, request, start_time, end_time, group_by):
        if group_by == "hour":
            data = get_total_storage_stats(start_time, end_time)
        elif group_by == "day":
            data = get_total_storage_stats_by_day(start_time, end_time)

        res_data = []
        for i in data:
            timestamp = int(time.mktime(i[0].timetuple()))
            select_time = time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime(timestamp))
            res_data.append({'datetime': select_time, 'total_storage': i[1]})
        return Response(sorted(res_data, key=lambda x: x['datetime']))


class ActiveUsersView(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    throttle_classes = (UserRateThrottle,)
    permission_classes = (IsAdminUser,)

    @check_parameter
    def get(self, request, start_time, end_time, group_by):
        if group_by == "hour":
            data = get_user_activity_stats(start_time, end_time)
        elif group_by == "day":
            data = get_user_activity_stats_by_day(start_time, end_time)

        res_data = []
        for i in data:
            timestamp = int(time.mktime(i[0].timetuple()))
            select_time = time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime(timestamp))
            res_data.append({'datetime': select_time, 'count': i[1]})
        return Response(sorted(res_data, key=lambda x: x['datetime']))
