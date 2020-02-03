from ckan.common import config, _
from ckan.lib.base import render_jinja2
from ckan.lib import mailer

MailerException = mailer.MailerException


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
