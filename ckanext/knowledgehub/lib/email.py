"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from ckan.common import config, _
from ckan.lib.base import render_jinja2
from ckan.lib import mailer
from ckan.plugins import toolkit
from logging import getLogger
from ckan.lib.helpers import url_for


MailerException = mailer.MailerException
log = getLogger(__name__)


def request_validation(admin, admin_email, resource_url):
    ''' Send request to specific user for data resource validation

    :param admin: The admin username
    :type admin: string
    :param admin_email: The admin email
    :type admin_email: string
    :param resource_url: The full URL to the resource
    :type resource_url: string
    '''
    if not admin:
        raise MailerException(_('Admin username not provided'))
    if not admin_email:
        raise MailerException(_('Admin email not provided'))
    if not resource_url:
        raise MailerException(_('Resource URL not provided'))

    site_title = config.get('ckan.site_title')
    body = render_jinja2('emails/request_access_body.txt', {
        'resource_url': resource_url,
        'site_title': site_title,
        'user_name': admin
    })
    subject = render_jinja2('emails/request_access_subject.txt', {
        'site_title': site_title
    })
    subject = subject.split('\n')[0]

    mailer.mail_recipient(admin, admin_email, subject, body, headers={})


def send_notification_email(recipient, template, data):
    '''Sends a notification email to a recipient given a template and data to
    render the email template.

    :param recipient: `str`, the id or the name of the recipient (CKAN user).
    :param template: `str`, the name of the template to render. The template
        file should reside in `templates/emails`. The name of the template file
        is generated from the template name by adding the suffix `.txt` for the
        email body and `<template>_subject.txt` for the email subject. The
        email subject can be overriden by providing `subject` value in the
        data to the template.
    :param data: `dict`, the data to be merged with the email template.
    '''
    user = toolkit.get_action('user_show')({
        'ignore_auth': True,
        'keep_email': True,
    }, {
        'id': recipient,
    })
    recipient_email = user.get('email')
    recipient_name = user.get('display_name') or user.get('fullname') or \
        user.get('username')
    if not recipient_email:
        raise MailerException(_('Unknown recipient email'))

    data['recipient'] = user
    data['has_group'] = False

    # Add group/organization if specified
    if data.get('group_id'):
        data['has_group'] = True
        action = 'organization_show'
        if data.get('group_type') == 'group':
            action = 'group_show'
        group = toolkit.get_action(action)({'ignore_auth': True},
                                           {'id': data['group_id']})
        data['group'] = group

    site_title = config.get('ckan.site_title')
    site_url = config.get('ckan.site_url')
    mail_data = {
        'site_title': site_title,
        'site_url': site_url,
        'h': _get_helpers(),
    }

    mail_data.update(data)
    template_path_body = 'emails/{}.txt'.format(template)
    template_path_subject = 'emails/{}_subject.txt'.format(template)

    subject = data.get('subject')
    if not subject:
        # try loading a subject template
        try:
            subject = render_jinja2(template_path_subject, mail_data)
        except Exception as e:
            log.exception(e)
            raise MailerException(e)

    subject = subject.strip().split('\n')[0]  # The subject can be only 1 line.

    body = render_jinja2(template_path_body, mail_data).strip()

    mailer.mail_recipient(recipient_name,
                          recipient_email,
                          subject,
                          body,
                          headers={})


def _get_helpers():
    return {
        'url_for': url_for,
    }
