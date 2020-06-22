from datetime import datetime
from mock import Mock, patch, MagicMock
from time import sleep

from ckanext.knowledgehub.lib.request_audit import RequestAudit
from ckanext.knowledgehub.model import RequestAudit as RequestAuditModel
from ckan.model import Session

from nose.tools import (
    assert_true,
    assert_equals,
    raises,
)


class TestRequestAudit:

    def test_store_log_data(self):
        Session.query(RequestAuditModel).delete()

        req_audit = RequestAudit()

        req_audit.log({
            'remote_ip': '192.168.1.10',
            'remote_user': 'test_user',
            'session': '123456789',
            'current_language': 'en',
            'access_time': datetime.now(),
            'request_url': '/test/url',
            'http_method': 'GET',
            'http_path': '/test/url?some=value',
            'http_query_params': 'some=value',
            'http_user_agent': 'Test Agent String',
            'client_os': 'linux',
            'client_device': 'firefox',
        })
        req_audit.log({
            'remote_ip': '192.168.1.10',
            'remote_user': 'test_user',
            'session': '123456789',
            'current_language': 'en',
            'access_time': datetime.now(),
            'request_url': '/test/url',
            'http_method': 'GET',
            'http_path': '/test/url?some=value',
            'http_query_params': 'some=value',
            'http_user_agent': 'Test Agent String',
            'client_os': 'linux',
            'client_device': 'firefox',
        })
        req_audit.log({
            'remote_ip': '192.168.1.10',
            'remote_user': 'test_user',
            'session': '123456789',
            'current_language': 'en',
            'access_time': datetime.now(),
            'request_url': '/test/url',
            'http_method': 'GET',
            'http_path': '/test/url?some=value',
            'http_query_params': 'some=value',
            'http_user_agent': 'Test Agent String',
            'client_os': 'linux',
            'client_device': 'firefox',
        })

        sleep(1)
        req_audit.shutdown()

        count, results = RequestAuditModel.get_all(offset=0, limit=10)
        assert_equals(count, 3)
