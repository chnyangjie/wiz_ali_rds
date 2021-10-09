import datetime
import json
import logging
import sys

from aliyunsdkcore.client import AcsClient
from aliyunsdkrds.request.v20140815.DescribeDBInstancePerformanceRequest import DescribeDBInstancePerformanceRequest
from aliyunsdkrds.request.v20140815.DescribeDBInstancesRequest import DescribeDBInstancesRequest
from aliyunsdkrds.request.v20140815.DescribeSlowLogRecordsRequest import DescribeSlowLogRecordsRequest


class AliRdsClient(object):
    METRICS = ["MySQL_MemCpuUsage", "MySQL_IOPS", "MySQL_DetailedSpaceUsage", "MySQL_NetworkTraffic", "MySQL_QPSTPS",
               "MySQL_Sessions"]

    def __init__(self, access_key_id, access_key, region):
        self.access_key_id = access_key_id
        self.access_key = access_key
        self.region = region

    def __enter__(self):
        self.client = AcsClient(self.access_key_id, self.access_key, self.region)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def query_rds_instance_metrics(self, instance_id: str, metrics_name_list: list, start_timestamp: float,
                                   end_timestamp: float):
        key = ','.join(metrics_name_list)
        request = DescribeDBInstancePerformanceRequest()

        request.set_StartTime(datetime.datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%dT%H:%MZ'))
        request.set_EndTime(datetime.datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%dT%H:%MZ'))
        request.set_Key(key)
        request.set_DBInstanceId(instance_id)

        response = json.loads(self.client.do_action_with_exception(request).decode())['PerformanceKeys'][
            'PerformanceKey']
        tmp = []
        for item in response:
            header = ["%s_%s(%s)" % (item['Key'], k, item['Unit']) for k in item['ValueFormat'].split("&")]
            value = [(dict(zip(header, [float(v) for v in i['Value'].split("&")])),
                      int(datetime.datetime.strptime(i['Date'], '%Y-%m-%dT%H:%M:%SZ').replace(
                          tzinfo=datetime.timezone.utc).timestamp())) for i in
                     item['Values']['PerformanceValue']]
            for k in header:
                for i in value:
                    d = {'instanceId': instance_id, 'Value': i[0][k], 'timestamp': i[1], 'metricName': k}
                    tmp.append(d)
        return tmp

    def query_rds_slow_log_detail(self, instance_id: str, start_timestamp: float, end_timestamp: float):
        page = 0
        size = 100
        total = sys.maxsize
        result = []
        while page * size < total:
            request = DescribeSlowLogRecordsRequest()
            request.set_DBInstanceId(instance_id)
            request.set_StartTime(datetime.datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%dT%H:%MZ'))
            request.set_EndTime(datetime.datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%dT%H:%MZ'))
            response = json.loads(self.client.do_action_with_exception(request).decode())
            page += 1
            total = response['TotalRecordCount']
            slow_query = response['Items']['SQLSlowRecord']
            result += slow_query
        return result

    def query_rds_instance_list(self) -> list:
        """
        DBInstanceId
        DBInstanceDescription
        DBInstanceClass
        ExpireTime
        :param client:
        :return:
        """
        logging.info("query for rds list")
        page = 0
        size = 100
        total = sys.maxsize
        instance_list = []

        while page * size < total:
            page += 1
            request = DescribeDBInstancesRequest()
            request.set_PageNumber(page)
            request.set_PageSize(size)
            response = self.client.do_action_with_exception(request).decode()
            response = json.loads(response)
            total = response['TotalRecordCount']
            instances = response['Items']['DBInstance']
            instance_list += instances
        return instance_list
