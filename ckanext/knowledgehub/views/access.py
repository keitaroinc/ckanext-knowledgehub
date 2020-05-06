import logging
import json

from flask import Blueprint
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request
from ckan.logic import (
    get_action,
    check_access,
    NotAuthorized,
    NotFound,
    ValidationError,
)


log = logging.getLogger(__name__)


access = Blueprint(
    u'access',
    __name__,
    url_prefix='/access',
)


def _get_context():
    return dict(model=model, user=g.user,
                auth_user_obj=g.userobj,
                session=model.Session)


def request(entity_type, entity_ref):
    context = _get_context()
    try:
        check_access('request_access', context, {})
    except NotAuthorized:
        base.abort(403, _('You do not have pemrission to request access '
                          'for this resource.'))
        return

    extra_vars = {}
    errors = []
    try:
        access_request = get_action('request_access')(context, {
            'entity_type': entity_type,
            'entity_ref': entity_ref,
        })
        extra_vars['access_request'] = access_request
    except NotAuthorized:
        errors.append(_('You do not have permission to request access for '
                        'this resource.'))
    except NotFound:
        errors.append(_('The referenced resource was not found.'))
    except ValidationError as e:
        for key, value in e.error_summary.items():
            errors.append('{} - {}'.format(key, value))
    except Exception as e:
        log.error('Failed to execute request_access. Error: %s', str(e))
        log.exception(e)
        base.abort(500, _('An unexpected error occured while processing your '
                          'request. Error: %s' % str(e)))
        return

    extra_vars['errors'] = errors

    return base.render('access/request.html', extra_vars=extra_vars)


access.add_url_rule('/request/<entity_type>/<entity_ref>', view_func=request)
