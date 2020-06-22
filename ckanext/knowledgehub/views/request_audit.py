import logging
import json
import math

from datetime import datetime, timedelta

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


# audit = Blueprint(
#     u'audit',
#     __name__,
#     url_prefix='/audit',
# )


def _get_context():
    return dict(model=model, user=g.user,
                auth_user_obj=g.userobj,
                session=model.Session)


def _extra_template_variables(context, data_dict):
    is_sysadmin = authz.is_sysadmin(g.user)
    try:
        user_dict = logic.get_action(u'user_show')({
            'ignore_auth': True,
        }, data_dict)
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


def _safe_int(value, default):
    try:
        if value is None or value == '':
            return default
        return int(value)
    except Exception as e:
        return default


def list_requests():
    context = _get_context()
    try:
        check_access('get_request_log', context, {})
    except logic.NotAuthorized:
        return base.abort(403, _('Not authorized to view requests audit.'))

    page = _safe_int(request.args.get('page', 1), 1)
    limit = _safe_int(request.args.get('limit', 20), 20)
    if page < 1:
        page = 1
    if limit < 1:
        limit = 20
    if limit > 500:
        limit = 500

    tab = request.args.get('tab', 'all')
    timespan = request.args.get('timespan')
    query = request.args.get('q', '').strip()

    errors = {}
    date_start = None
    date_end = None

    if timespan == 'last-hour':
        date_start = datetime.now() - timedelta(hours=1)
    elif timespan == 'last-day':
        date_start = datetime.now() - timedelta(days=1)
    elif timespan == 'last-week':
        date_start = datetime.now() - timedelta(days=7)
    elif timespan == 'last-month':
        date_start = datetime.now() - timedelta(days=30)
    elif timespan == 'custom':
        date_vals = {}
        for key in ['date_start', 'date_end']:
            value = request.args.get(key)
            if value:
                try:
                    value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                    date_vals[key] = value
                except Exception as e:
                    errors[key] = [_('Invalid value. Should be a formatted '
                                     'date string like "2020-10-21 10:35:43"')]

        date_start = date_vals.get('date_start')
        date_end = date_vals.get('date_end')

    extra_vars = _extra_template_variables(context, {
        'user_obj': g.userobj,
        'user': g.userobj,
    })

    extra_vars['errors'] = errors

    if tab == 'all':
        try:
            log_data = get_action('get_request_log')(context, {
                'page': page,
                'limit': limit,
                'date_start': date_start,
                'date_end': date_end,
                'q': query,
            })
        except Exception as e:
            log.exception(e)
            errors['general'] = _('An error occured while trying to '
                                  'get the requests log.')
            log_data = {
                'results': [],
                'count': 0,
            }
    else:
        report = {
            'page_count': 'endpoint',
            'user_count': 'remote_user',
            'ip_count': 'remote_ip',
        }.get(tab)
        try:
            log_data = get_action('get_request_log_report')(context, {
                'report': report,
                'date_start': date_start,
                'date_end': date_end,
                'page': page,
                'limit': limit,
                'q': query,
            })
        except Exception as e:
            log.exception(e)
            errors['general'] = _('An error occured while trying to '
                                  'get the report.')
            log_data = {
                'results': [],
                'count': 0,
            }

    extra_vars['results'] = log_data.get('results')
    extra_vars.update({
        'tab': tab,
        'page': page,
        'limit': limit,
        'timespan': timespan,
        'date_start': date_start.strftime(
            '%Y-%m-%d %H:%M:%S') if date_start else '',
        'date_end': date_start.strftime(
            '%Y-%m-%d %H:%M:%S') if date_end else '',
        'q': query,
    })

    def _get_page_data():
        current_page = page or 1
        query_params = dict(filter(lambda (k, v): k != 'page',
                                   request.args.items()))
        pages = []
        total_pages = int(math.ceil(log_data.get('count', 0) / float(limit)))

        pagination = {
            'current_page': current_page,
            'pages': pages,
            'previous_url': '',
            'next_url': '',
            'total_pages': total_pages,
            'total_items': log_data.get('count', 0),
            'limit': limit,
        }

        start = 1
        if current_page > 3:
            start = current_page - 3
        end = current_page + 3
        if end > total_pages:
            end = total_pages

        for i in range(start, end + 1):
            query_params['page'] = i
            url = h.url_for('user_dashboard.audit_requests', **query_params)
            pages.append({
                'page': i,
                'url': url,
            })

        if current_page > 1:
            query_params['page'] = current_page - 1
            pagination['previous_url'] = h.url_for(
                'user_dashboard.audit_requests',
                **query_params
            )

        if current_page < total_pages:
            query_params['page'] = current_page + 1
            pagination['next_url'] = h.url_for(
                'user_dashboard.audit_requests',
                **query_params
            )

        return pagination

    extra_vars['pagination'] = _get_page_data()

    if tab == 'all':
        return base.render('request_audit/requests_list.html',
                           extra_vars=extra_vars)

    return base.render('request_audit/requests_report.html',
                       extra_vars=extra_vars)


def register_url_rules(user_dashboard_blueprint):
    user_dashboard_blueprint.add_url_rule(
        '/audit/requests',
        view_func=list_requests,
        endpoint='audit_requests',
    )
