from mock import Mock, MagicMock
import nose.tools
import os

from ckan.tests import helpers
from ckan.plugins import toolkit
from ckan import plugins
from ckan.lib import mailer
from ckanext.knowledgehub.lib.util import monkey_patch
from ckanext.knowledgehub.tests.helpers import get_context
from hdx.hdx_configuration import Configuration

from ckanext.knowledgehub.lib.email import (
    request_validation,
    send_notification_email,
)
from logging import getLogger

assert_equals = nose.tools.assert_equals

log = getLogger(__name__)


class TestEmailNotification(helpers.FunctionalTestBase):

    @monkey_patch(Configuration, 'delete', MagicMock())
    @monkey_patch(Configuration, 'create', MagicMock())
    def setup(self):
        helpers.reset_db()
        if not plugins.plugin_loaded('datastore'):
            plugins.load('datastore')
        if not plugins.plugin_loaded('knowledgehub'):
            plugins.load('knowledgehub')

    @classmethod
    def teardown_class(self):
        if not plugins.plugin_loaded('knowledgehub'):
            plugins.unload('knowledgehub')
        if not plugins.plugin_loaded('datastore'):
            plugins.unload('datastore')
        # if not plugins.plugin_loaded('datapusher'):
        #     plugins.unload('datapusher')

    @monkey_patch(mailer, 'mail_recipient', MagicMock())
    def test_request_validation(self):
        request_validation('user_admin', 'user_admin@example.com',
                           '/resource/1')
        assert_equals(mailer.mail_recipient.call_count, 1)

    @monkey_patch(mailer, 'mail_recipient', MagicMock())
    def test_send_notification_email(self):

        ctx = get_context()
        user = ctx['auth_user_obj']

        data = {
            'package': {
                'type': 'package',
                'package': {
                    'id': 'pkg-id',
                    'title': 'Package 1',
                }
            },
            'dashboard': {
                'type': 'dashboard',
                'dashboard': {
                    'id': 'dash-1',
                    'title': 'Dashboard 1',
                }
            }
        }

        organization = toolkit.get_action('organization_create')({
            'ignore_auth': True,
            'user': ctx['user'],
        }, {
            'name': 'org-1',
            'title': 'Organization 1',
        })

        group = toolkit.get_action('group_create')({
            'ignore_auth': True,
            'user': ctx['user'],
        }, {
            'name': 'group',
            'title': 'Group 1',
        })

        for template in ['notification_access_granted',
                         'notification_access_revoked']:
            for _type in ['package', 'dashboard']:
                email_data = {}
                email_data.update(data[_type])
                send_notification_email(user.id, template, email_data)
                for group_type, grp in [('organization', organization),
                                        ('group', group)]:
                    email_data = {
                        'group_type': group_type,
                        'group_id': grp['id'],
                    }
                    email_data.update(data[_type])
                    log.debug('Testing send_notification_email: '
                              'user=%s, '
                              'template=%s'
                              'data=%s', user.id, template, email_data)
                    send_notification_email(user.id, template, email_data)

        assert_equals(mailer.mail_recipient.call_count, 12)
