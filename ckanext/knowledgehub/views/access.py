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

import logging
import json

from flask import Blueprint
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan import authz
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


def _extra_template_variables(context, data_dict):
    is_sysadmin = authz.is_sysadmin(g.user)
    try:
        user_dict = logic.get_action(u'user_show')(context, data_dict)
    except logic.NotFound:
        h.flash_error(_(u'Not authorized to see this page'))
        return
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    is_myself = user_dict[u'name'] == g.user
    about_formatted = h.render_markdown(user_dict[u'about'])
    extra = {
        u'is_sysadmin': is_sysadmin,
        u'user_dict': user_dict,
        u'is_myself': is_myself,
        u'about_formatted': about_formatted
    }
    return extra


def request_access(entity_type, entity_ref):
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


def requests_list():
    context = _get_context()
    check_access('access_request_list', context, {})

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    extra_vars = _extra_template_variables(context, {
        'user_obj': g.userobj,
        'user': g.userobj,
    })

    return base.render('access/requests_list.html', extra_vars=extra_vars)


def grant(id):
    context = _get_context()
    try:
        check_access('access_request_grant', context, {})
    except NotAuthorized:
        base.abort(403, _('You do not have permission to grant '
                          'access to this resource.'))

    access_request = get_action('access_request_grant')(context, {'id': id})

    try:
        user = get_action('user_show')({'ignore_auth': True},
                                       {'id': access_request.get('user_id')})
        access_request['user'] = user
    except Exception as e:
        log.error('Error while fetching user for access request. Error: %s',
                  str(e))
        log.exception(e)
        base.abort(500, _('An unexpected error occured while trying to '
                          'grant access. Error: {}').format(str(e)))

    extra_vars = _extra_template_variables(context, {
        'user_obj': g.userobj,
        'user': g.userobj,
    })

    extra_vars.update({
        'access_request': access_request,
    })

    return base.render('access/granted.html', extra_vars)


def decline(id):
    context = _get_context()
    try:
        check_access('access_request_decline', context, {})
    except NotAuthorized:
        base.abort(403, _('You do not have permission to decline the request '
                          'for access to this resource.'))

    access_request = get_action('access_request_decline')(context, {'id': id})

    try:
        user = get_action('user_show')({'ignore_auth': True},
                                       {'id': access_request.get('user_id')})
        access_request['user'] = user
    except Exception as e:
        log.error('Error while fetching user for access request. Error: %s',
                  str(e))
        log.exception(e)
        base.abort(500, _('An unexpected error occured while trying to '
                          'grant access. Error: {}').format(str(e)))

    extra_vars = _extra_template_variables(context, {
        'user_obj': g.userobj,
        'user': g.userobj,
    })

    extra_vars.update({
        'access_request': access_request,
    })

    return base.render('access/declined.html', extra_vars)


def register_url_rules(user_dashboard_blueprint):
    user_dashboard_blueprint.add_url_rule('/access_requests',
                                          view_func=requests_list,
                                          strict_slashes=False)


access.add_url_rule('/request/<id>/grant', view_func=grant)
access.add_url_rule('/request/<id>/decline', view_func=decline)
access.add_url_rule('/request/<entity_type>/<entity_ref>',
                    view_func=request_access)
