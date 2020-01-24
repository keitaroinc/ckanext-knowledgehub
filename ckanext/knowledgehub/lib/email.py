from ckan.common import config, _
from ckan.lib.base import render_jinja2
from ckan.lib import mailer

MailerException = mailer.MailerException


def request_validation(user, resource_url):
    ''' Send request to specific user for data resource validation

    :param user: The user object
    :type user: object
    :param resource_url: the full URL to the resource
    :type resource_url: string
    '''
    if not user:
        raise MailerException(_('User object not provided'))
    if not resource_url:
        raise MailerException(_('Resource URL not provided'))

    site_title = config.get('ckan.site_title')
    body = render_jinja2('emails/request_access_body.txt', {
        'resource_url': resource_url,
        'site_title': site_title,
        'user_name': user.name
    })
    subject = render_jinja2('emails/request_access_subject.txt', {
        'site_title': site_title
    })
    subject = subject.split('\n')[0]

    mailer.mail_recipient(user.name, user.email, subject, body, headers={})
