import logging
import os
import pkgutil
import inspect
import uuid
import json
import functools32
import requests
import re
import pytz
import humanize
import pycountry

from datetime import datetime, timedelta
from dateutil import parser
from dateutil.tz import tzlocal
from flask import Blueprint
from urllib import urlencode
from six import string_types, iteritems
from enum import Enum
from hdx.data.dataset import Dataset
from werkzeug import UserAgent


try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

import ckan.plugins.toolkit as toolkit
import ckan.model as model
from ckan.common import g, _, request, is_flask_request, c
from ckan import logic
from ckan.model import ResourceView, Resource
from ckan import lib
from ckan.lib import helpers as h
from ckan.controllers.admin import get_sysadmins
from ckan.logic import ValidationError

from ckanext.knowledgehub.model import Dashboard
from ckanext.knowledgehub.model import ResourceValidation
from ckanext.knowledgehub.model import Comment
from ckanext.knowledgehub.lib.request_audit import get_request_audit


log = logging.getLogger(__name__)
model_dictize = lib.dictization.model_dictize


SYSTEM_RESOURCE_TYPE = 'system_merge'
INVALID_COLUMN_NAMES = ['_id', '_full_text']


def _get_context():
    context = dict(model=model,
                   user=g.user,
                   auth_user_obj=g.userobj)
    return context


def _register_blueprints():
    u'''Return all blueprints defined in the `views` folder
    '''
    blueprints = []

    def is_blueprint(mm):
        return isinstance(mm, Blueprint)

    path = os.path.join(os.path.dirname(__file__), 'views')

    for loader, name, _ in pkgutil.iter_modules([path]):
        module = loader.find_module(name).load_module(name)
        for blueprint in inspect.getmembers(module, is_blueprint):
            blueprints.append(blueprint[1])
            log.debug(u'Registered blueprint: {0!r}'.format(blueprint[0]))
    return blueprints


def _get_functions(module_root, functions={}):
    u'''
     Helper function that scans extension
     specified dir for all functions.
     '''
    for module_name in ['create', 'update', 'delete', 'get']:
        module_path = '%s.%s' % (module_root, module_name,)

        module = __import__(module_path)

        for part in module_path.split('.')[1:]:
            module = getattr(module, part)

        for key, value in module.__dict__.items():
            if not key.startswith('_') \
                    and (hasattr(value, '__call__')
                         and (value.__module__ == module_path)):
                functions[key] = value

    return functions


def id_to_title(model, id):
    data_dict = {}
    data_dict['id'] = id
    if model:
        entry = toolkit.get_action('{}_show'.format(model))({}, data_dict)
    return entry.get('title') or entry.get('name')


def get_rq_options(context={'ignore_auth': True}, idValue=False):
    if not context:
        context = _get_context()
    rq_options = []
    rq_list = toolkit.get_action('research_question_list')(context, {})

    for rq in rq_list.get(u'data', []):
        if idValue:
            opt = {u'text': rq[u'title'],
                   u'value': rq[u'id']}
        else:
            opt = {u'text': rq[u'title'],
                   u'value': rq[u'title'], u'id': rq[u'id']}
        rq_options.append(opt)
    return rq_options


def get_theme_options():
    context = _get_context()
    theme_options = []
    theme_list = toolkit.get_action('theme_list')(context, {})
    for theme in theme_list.get(u'data', []):
        opt = {u'text': theme[u'title'], u'value': theme[u'title']}
        theme_options.append(opt)
    theme_options.insert(0, {'text': 'Select theme', 'value': ''})
    return theme_options


def get_resource_validation_options(pkg_id_or_name):
    context = _get_context()
    usr = context.get('user')
    user = model.User.by_name(usr.decode('utf8')).id
    pkg = toolkit.get_action('package_show')(context, {u'id': pkg_id_or_name})
    org_id = pkg['organization']['id']
    member_list = toolkit.get_action(
        'organization_show')(context, {u'id': org_id})
    admins = []
    for member in member_list.get(u'users', []):
        if member[u'capacity'] == u'admin':
            if member[u'id'] != user:
                opt = {u'text': member[u'name'], u'value': member[u'name']}
                admins.append(opt)
    admins.insert(
        0,
        {
            'text': 'Select the organization admin for validation request',
            'value': ''
        })
    return admins


def check_resource_status(resource_id):
    rv = ResourceValidation.get(
        resource=resource_id
    ).first()

    return rv.status if rv else 'not_validated'


def check_validation_admin(resource_id):
    context = _get_context()
    usr = context.get('user')
    user = model.User.by_name(usr.decode('utf8')).name
    rv = ResourceValidation.get(
        resource=resource_id
    ).first()

    return user == rv.admin if rv else False


def get_sub_theme_options():
    context = _get_context()
    sub_theme_options = []
    sub_theme_list = toolkit.get_action('sub_theme_list')(context, {})
    for sub_theme in sub_theme_list.get(u'data', []):
        opt = {u'text': sub_theme[u'title'], u'value': sub_theme[u'title']}
        sub_theme_options.append(opt)
    sub_theme_options.insert(0, {'text': 'Select sub-theme', 'value': ''})
    return sub_theme_options


def resource_view_get_fields(resource):

    if not resource.get('datastore_active'):
        return []

    data = {
        'resource_id': resource['id'],
        'limit': 0
    }
#   result = logic.get_action('datastore_search')({}, data)
    try:
        result = logic.get_action('datastore_search')({}, data)
        fields = [field['id'] for field in result.get('fields', [])]

#    fields = [field['id'] for field in result.get('fields', [])]
        return sorted(fields)

#    return sorted(fields)
    except logic.NotFound:
        return []


def _isnt_id(v):
    return v['id'] != '_id'


def get_resource_columns(res_id, escape_columns=[]):
    '''

    Get the names of the columns for the resource stored in Datastore

        - res_id: (string) ID of the CKAN resource
        - escape_columns: (array) names of the columns that should be omitted

    '''
    data = {
        'resource_id': res_id,
        'limit': 0
    }
    try:
        result = toolkit.get_action('datastore_search')({}, data)
    except Exception:
        return []

    fields = [field['id'] for field in result.get('fields', [])
              if field['id'] not in escape_columns and _isnt_id(field)]

    return fields


def get_resource_numeric_columns(res_id):
    '''

    Get the names of the numeric columns for the resource stored in Datastore

        - res_id: (string) ID of the CKAN resource

    '''
    data = {
        'resource_id': res_id,
        'limit': 0
    }

    try:
        result = toolkit.get_action('datastore_search')({}, data)
    except Exception:
        return []

    fields = [field['id'] for field in result.get('fields', [])
              if field['type'] == 'numeric' and _isnt_id(field)]

    return fields


def get_chart_types():
    '''
    Get all available types of chart following c3 specification
    :return:
    '''
    chart_types = [
        {'text': _('Line'), 'value': 'line'},
        {'text': _('Bar'), 'value': 'bar'},
        {'text': _('Horizontal bar'), 'value': 'hbar'},
        {'text': _('Stacked bar'), 'value': 'sbar'},
        {'text': _('Stacked horizontal bar'), 'value': 'shbar'},
        {'text': _('Butterfly'), 'value': 'buttchart'},
        {'text': _('Area'), 'value': 'area'},
        {'text': _('Stacked area'), 'value': 'area-spline'},
        {'text': _('Spline'), 'value': 'spline'},
        {'text': _('Donut'), 'value': 'donut'},
        {'text': _('Pie'), 'value': 'pie'},
        {'text': _('Scatter'), 'value': 'scatter'},
        {'text': _('Bubble'), 'value': 'bscatter'}
    ]
    return chart_types


def get_uuid():
    return uuid.uuid4()


def get_visualization_size():
    '''
    Get available sizes for displaying visualizations: charts, text box
    :return:
    '''
    options = [{'text': _('Small'), 'value': 'small'},
               {'text': _('Medium'), 'value': 'medium'},
               {'text': _('Large'), 'value': 'large'}]
    return options


def get_color_scheme():
    '''
    Get color schemes for displaying the charts
    :return:
    '''
    colors = [{'value': '#00B398',
               'text': _('Green')},
              {'value': '#0072BC',
               'text': _('Blue')},
              {'value': '#18375F',
               'text': _('Navy Blue')},
              {'value': '#338EC9',
               'text': _('Light Blue')},
              {'value': '#F5C205',
               'text': _('Yellow')},
              {'value': '#CCCCCC',
               'text': _('Gray')},
              {'value': '#00000',
               'text': _('Black')},
              {'value': '#EF4A60',
               'text': _('Red')}
              ]

    return colors


def get_map_color_scheme():
    '''
    Get color schemes for displaying the maps
    :return:
    '''
    colors = [
        {
            'value': '#CCE3F2,#99C7E4,#66AAD7,#338EC9,#0072BC',
            'text': _('Blue')
        },
        {
            'value': '#FDF3CD,#FBE79B,#F9DA69,#F7CE37,#F5C205',
            'text': _('Yellow')
        },
        {
            'value': '#CCF0EA,#99E1D6,#66D1C1,#33C2AD,#00B398',
            'text': _('Green')
        },
        {
            'value': '#D1D7DF,#A3AFBF,#74879F,#465F7F,#18375F',
            'text': _('Navy Blue')
        },
        {
            'value': '#E5E5E5,#CCCCCC,#999999,#666666,#333333',
            'text': _('Gray')
        },
        {
            'value': '#FCDBDF,#F9B7BF,#F592A0,#F26E80,#EF4A60',
            'text': _('Red')
        }
    ]

    return colors


def parse_json(string):
    return json.loads(string)


def get_chart_sort():
    '''
    Get available values for sorting charts data
    :return:
    '''
    options = [{'text': _('Default'), 'value': 'default'},
               {'text': _('Ascending'), 'value': 'asc'},
               {'text': _('Descending'), 'value': 'desc'}]
    return options


def get_tick_text_rotation():
    '''
    Get available options for rotating chart x axis
    :return:
    '''
    options = [{'text': _('Horizontal'), 'value': '0'},
               {'text': _('Diagonal'), 'value': '30'},
               {'text': _('Vertical'), 'value': '90'},
               {'text': _('Reverse'), 'value': '180'}]

    return options


def get_data_formats(num=None):
    '''
    Get available formats for charts tooltip and axis ticks
    :return:
    '''
    options = [{'text': _('Default'), 'value': ''},
               {'text': _('Integer e.g 2'), 'value': '.0f'},
               {'text': _('Decimal (1 digit) e.g 2.5'), 'value': '.1f'},
               {'text': _('Decimal (2 digit) e.g 2.50'), 'value': '.2f'},
               {'text': _('Decimal (3 digit) e.g 2.501'), 'value': '.3f'},
               {'text': _('Decimal (4 digit) e.g 2.5012'), 'value': '.4f'},
               {'text': _('Currency e.g. $2,000'), 'value': '$'},
               {'text': _('Rounded e.g 2k'), 'value': 's'},
               {'text': _('Percentage (0 digit) e.g 25% for 0.25'),
                   'value': '.0%'},
               {'text': _('Percentage (1 digit) e.g 25.1% for 0.251'),
                   'value': '.1%'},
               {'text': _('Percentage (2 digit) e.g 25.12% for 0.2512'),
                   'value': '.2%'},
               {'text': _('Comma thousands separator (0 digit) e.g 2,512'),
                   'value': ',.0f'},
               {'text': _('Comma thousands separator (1 digit) e.g 2,512.3'),
                   'value': ',.1f'},
               {'text': _('Comma thousands separator (2 digit) e.g 2,512.34'),
                   'value': ',.2f'}]
    if num:
        return options[:num]
    return options


def dump_json(value):
    return json.dumps(value)


@functools32.lru_cache(maxsize=128)
def get_resource_data(sql_string):
    '''
    Get the records for the vizialization in a format:
        [{u'2009':u'1.6',u'os': u'Android'}, {u'2009':u'10.5',u'os': u'iOS'}]

    - sql_string: the SQL query that will be used for datastore_search_sql
    '''

    sysadmin = get_sysadmins()[0].name
    context = {'user': sysadmin, 'ignore_auth': True}

    response = toolkit.get_action('datastore_search_sql')(
        context, {'sql': sql_string}
    )
    records_to_lower = []
    for record in response['records']:
        records_to_lower.append({k.lower(): v for k, v in record.items()})

    return records_to_lower


# get the titles for the RQs from the resource ID
def get_rq_titles_from_res(res_id):

    pkg_id = model.Session.query(Resource.package_id)\
        .filter(Resource.id == res_id).all()
    only_id = pkg_id[0]
    package_sh = toolkit.get_action('package_show')({}, {'id': only_id[0]})
    if not package_sh.get('research_question'):
        return 0
    rqs = package_sh['research_question']
    list_rqs = pg_array_to_py_list(rqs)
    titles = rq_ids_to_titles(list_rqs)
    list_titles = []

    for tit in titles:
        clean = tit.replace("'", "")
        list_titles.append(clean)
    return list_titles


# get the ids for the RQs from the resource ID
def get_rq_ids(res_id):
    pkg_id = model.Session.query(Resource.package_id)\
        .filter(Resource.id == res_id).all()
    only_id = pkg_id[0]
    package_sh = toolkit.get_action('package_show')({}, {'id': only_id[0]})
    if not package_sh.get('research_question'):
        return 0
    rqs = package_sh['research_question']
    return rqs


def get_last_visuals():

    res_views = model.Session.query(ResourceView)\
        .filter(ResourceView.view_type == 'chart')\
        .limit(3).all()
    data_dict_format = model_dictize\
        .resource_view_list_dictize(res_views, _get_context())
    try:
        toolkit.check_access('user_profile_show', _get_context())
    except toolkit.NotAuthorized:
        log.debug('Not Authorized')
        data_dict_format = {}
    return data_dict_format


def get_rqs_dashboards(rq_id):

    visualizations = toolkit.get_action('dashboards_for_rq')(_get_context(), {
        'research_question': rq_id,
        'ignore_permissions': True,
    })

    return visualizations


def get_filter_values(resource_id, filter_name, previous_filters=[]):
    '''Returns resource field values with no duplicates.'''

    sysadmin = get_sysadmins()[0].name
    context = {'user': sysadmin, 'ignore_auth': True}

    resource = toolkit.get_action('resource_show')(context,
                                                   {'id': resource_id})

    if not resource.get('datastore_active'):
        return []

    data = {
        'resource_id': resource['id'],
        'limit': 0
    }
    result = toolkit.get_action('datastore_search')(context, data)

    where_clause = _create_where_clause(previous_filters)

    fields = [field['id'] for field in result.get('fields', [])]
    values = []

    if filter_name in fields:

        sql_string = u'''SELECT DISTINCT "{column}"
         FROM "{resource}" {where}'''.format(
            column=filter_name,
            resource=resource_id,
            where=where_clause
        )

        result = toolkit.get_action('datastore_search_sql')(
            context, {'sql': sql_string}
        )
        values = [field[filter_name] for field in result.get('records', [])]

    return sorted(values)


def _create_where_clause(filters):

    where_clause = u''

    if any(filters):
        if len(filters) > 1:
            # Loop through filters and create SQL query
            for idx, _ in enumerate(filters):
                op = u'='
                name = _['name']
                value = _['value']

                if idx == 0:
                    where_clause = u'WHERE ("{0}" {1} \'{2}\')'.format(
                        name, op, value)
                else:
                    operator = _['operator']
                    where_clause += u' ' + operator + u' ("{0}" {1} \'{2}\')'.\
                        format(name, op, value)

        else:
            _ = filters[0]
            op = u'='
            name = _['name']
            value = _['value']
            where_clause = \
                u'WHERE ("{0}" {1} \'{2}\')'.format(
                    name,
                    op,
                    value
                )
    return where_clause


def get_rq(limit, order_by):
    context = _get_context()
    rq_list = toolkit.get_action('research_question_list')(context, {
        'pageSize': limit,
        'order_by': order_by
    })

    return rq_list


# Helper for transforming postgres array
# type to python list type
def pg_array_to_py_list(rq_list):

    result = []
    if rq_list.startswith('{'):
        ids = rq_list.replace('{', '').replace('}', '').split(',')
        for id in ids:
            result.append(_normalize_pg_string(id))
    else:
        result.append(rq_list)
    return result


def _normalize_pg_string(s):

    if len(s.split(' ')) > 1:
        result = s[1:-1]
    else:
        result = s
    return result


# Overwrite of the original 'resource_view_icon'
# in order to support new resource view types
def resource_view_icon(view):
    '''
    Returns the icon for a particular view type.
    '''
    if view.get('view_type') == 'chart':
        return 'bar-chart'
    elif view.get('view_type') == 'table':
        return 'table'
    elif view.get('view_type') == 'map':
        return 'map'
    else:
        return 'exclamation'


def knowledgehub_get_map_config():

    map_config = {
        'osm_url': config.get('ckanext.knowledgehub.map_osm_url',
                              'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}'
                              '.png'),
        'osm_attribute': config.get('ckanext.knowledgehub.map_osm_attribute',
                                    '&copy; <a '
                                    'href="https://www.openstreetmap.org'
                                    '/copyright">'
                                    'OpenStreetMap</a>'
                                    ' contributors')
    }
    return json.dumps(map_config)


def get_single_rq(rq_id):
    context = _get_context()
    try:
        rq = toolkit.get_action(
            'research_question_show')(context, {'id': rq_id})
    except Exception as e:
        log.debug('Error get_single_rq: %s' % str(e))
        return {}

    return rq


def rq_ids_to_titles(rq_ids):
    if not isinstance(rq_ids, list):
        rq_ids = pg_array_to_py_list(rq_ids)
    rqs = []
    context = _get_context()

    for rq_id in rq_ids:
        try:
            rq = toolkit.get_action(
                'research_question_show')(context, {'id': rq_id})
            rqs.append(rq.get('title'))
        except logic.NotFound:
            continue

    return rqs


def get_geojson_resources():

    context = _get_context()

    q = model.Session.query(model.Resource) \
        .filter(model.Resource.format == 'GeoJSON').all()
    list_resources = model_dictize.resource_list_dictize(q, context)

    return [{'text': r['name'], 'value': r['url']}
            for r in list_resources]
    return []


def get_dataset_url_path(url):
    # Remove http://host:port/lang part
    parts = url.split('/dataset')
    if len(parts) == 1:
        return ''
    return '/dataset%s' % parts[1]


def get_map_data(geojson_url, map_key_field, data_key_field,
                 data_value_field, from_where_clause):

    geojson_keys = []

    username = None
    if hasattr(g, 'user'):
        username = g.user

    user = model.User.by_name(username)
    context = {
            'user': user.get('name'),
            'auth_user_obj': user,
            'model': model,
            'user': username
        }
    user_dict = model_dictize.user_dictize(user, context)

    # give the apikey to requests, so the geojson file is accessible
    resp = requests.get(geojson_url, headers={
        'Authorization': user_dict.get('apikey'),
    })

    try:
        geojson_data = resp.json()
    except ValueError as e:
        # includes simplejson.decoder.JSONDecodeError
        raise ValueError('Invalid JSON syntax: %s' %
                         (e))

    for feature in geojson_data['features']:
        geojson_keys.append(feature['properties'][map_key_field])

    sql = u'SELECT ' + u'"' + data_key_field + \
          u'", MAX("' + data_value_field + u'") as ' + \
          u'"' + data_value_field + u'"' + from_where_clause + \
          u' GROUP BY "' + data_key_field + u'"'

    response = toolkit.get_action('datastore_search_sql')(
        {}, {'sql': sql}
    )
    records_to_lower = []
    for record in response['records']:
        records_to_lower.append({k.lower(): v for k, v in record.items()})
    response['records'] = records_to_lower

    mapping = {}

    for record in records_to_lower:

        key = record[data_key_field.lower()]
        value = record[data_value_field.lower()]

        if key not in geojson_keys:
            continue

        mapping[key] = {
            'key': key,
            'value': value
        }

    map_data = {
        'geojson_data': geojson_data,
        'features_values': mapping
    }

    return map_data


# Gets the properties from the geojson file, to populate the dropdowns
def get_geojson_properties(url, username):
    # TODO handle if no url
    # TODO handle topojson format

    user_dict = toolkit.get_action('user_show')(
                {'ignore_auth': True}, {'id': username})

    # give the apikey to requests, so the geojson file is accessible
    resp = requests.get(url, headers={
        'Authorization': user_dict.get('apikey'),
    })

    geojson = resp.json()
    result = []
    exclude_keys = [
        'marker-symbol',
        'marker-color',
        'marker-size',
        'stroke',
        'stroke-width',
        'stroke-opacity',
        'fill',
        'fill-opacity'
    ]

    for k, v in geojson.get('features')[0].get('properties').iteritems():
        if k not in exclude_keys:
            result.append({'value': k, 'text': k})
    return result


# Returns the total number of feedbacks for given type
def resource_feedback_count(type, resource, dataset):
    context = _get_context()
    filter = {
        'type': type,
        'resource': resource,
        'dataset': dataset
    }

    try:
        rf_list = toolkit.get_action('resource_feedback_list')(context, filter)
    except Exception:
        return 0

    return rf_list.get('total', 0)


def get_dashboards(ctx={}, limit=5, order_by='created_by asc'):
    if not ctx:
        ctx = _get_context()
    dashboards = toolkit.get_action('dashboard_list')(
        ctx,
        {'limit': limit, 'sort': order_by}
    )

    return dashboards.get('data', [])


def remove_space_for_url(str):
    return str.replace(" ", "-")


def format_date(date_str):

    # split date & time
    if isinstance(date_str, datetime):
        date_str = date_str.isoformat()

    date = date_str.split('T')  # date[0] is the date, date[1] is the time
    time_basic = date[1].split('.')  # time_basic[0] = hh/mm/ss
    # remove seconds
    time_basic[0] = time_basic[0][:-3]
    display_date = date[0] + ' at ' + time_basic[0]
    return display_date


def calculate_time_passed(str):

    now = datetime.now(tzlocal())
    new_date = str.split('T')
    new_date = ' '.join(new_date)

    date_time_obj = datetime.strptime(new_date, '%Y-%m-%d %H:%M:%S.%f')

    now_aware = pytz.utc.localize(date_time_obj)
    diff = humanize.naturaltime(now - now_aware)

    return diff


def _get_pager(results, item_type):

    def _get_url(*args, **kwargs):
        page = kwargs.get('page', g.page.page)
        params = filter(lambda p: p[0] not in ['page', '_search-for'],
                        [(k, v.encode('utf-8')
                          if isinstance(v, string_types) else str(v))
                         for k, v in request.params.items()])
        params.append(('page', page))
        params.append(('_search-for', item_type))
        return request.path + '?' + urlencode(params)

    return h.Page(
        collection=results.get('results', []),
        page=results.get('page', 1),
        item_count=results.get('count'),
        items_per_page=results.get('limit'),
        url=_get_url
    )


def get_tab_url(tab):
    params = filter(lambda p: p[0] not in ['page', '_search-for'],
                    [(k, v.encode('utf-8')
                      if isinstance(v, string_types) else str(v))
                     for k, v in request.params.items()])
    if tab != 'package':
        params.append(('_search-for', tab))
    return request.path + ('?' + urlencode(params) if params else '')


def get_active_tab():
    active_tab = request.params.get('_search-for')
    if active_tab and active_tab.strip():
        return active_tab.strip()
    return 'package'


def _get_sort():
    sort = request.params.get('sort', '').strip()
    return sort.replace('title_string', 'title')


def _get_facets():
    facets = []
    for param, value in request.params.items():
        if param in ['organization', 'groups', 'tags']:
            facets.append('%s:%s' % (param, value))

    return facets


def get_searched_rqs(query):
    context = _get_context()
    search_query = {
        'text': query,
        'page': int(request.params.get('page', 1)),
        'facet': True
    }
    sort = _get_sort()
    facets = _get_facets()
    if sort:
        search_query['sort'] = sort
    if facets:
        search_query['fq'] = facets
    list_rqs_searched = toolkit.get_action(
        'search_research_questions')(
            context,
            search_query)
    list_rqs_searched['pager'] = _get_pager(list_rqs_searched,
                                            'research-questions')

    c.search_facets = list_rqs_searched['search_facets']
    return list_rqs_searched


def get_searched_dashboards(query):
    page = int(request.params.get('page', 1))
    limit = int(config.get('ckan.datasets_per_page', 20))
    offset = (page - 1) * limit
    list_dash_searched = {
        'count': 0,
        'limit': limit,
        'stats': {},
        'search_facets': {},
        'results': []
    }

    def result_iter(page=1):
        search_query = {
            'text': query,
            'facet': True
        }
        sort = _get_sort()
        facets = _get_facets()
        if sort:
            search_query['sort'] = sort
        if facets:
            search_query['fq'] = facets
        while True:
            search_query['page'] = page
            dashboards = toolkit.get_action('search_dashboards')(
                _get_context(),
                search_query)

            results = dashboards.get('results', [])
            if not results:
                break

            for k, v in iteritems(dashboards.get('search_facets', {})):
                if list_dash_searched.get('search_facets').get(k):
                    list_dash_searched['search_facets'][k].update(v)
                else:
                    list_dash_searched['search_facets'][k] = v

            for r in results:
                yield r
            page += 1

    dashboards = []
    for dashboard in result_iter():
        try:
            toolkit.check_access(
                'dashboard_show',
                _get_context(),
                {'name': dashboard.get('name')})
        except toolkit.NotAuthorized:
            continue

        dashboards.append(dashboard)

    list_dash_searched['count'] = len(dashboards)
    list_dash_searched['results'] = dashboards[offset:offset+limit]
    list_dash_searched['pager'] = _get_pager(list_dash_searched, 'dashboards')

    c.search_facets = list_dash_searched['search_facets']
    return list_dash_searched


def get_searched_visuals(query):
    context = _get_context()
    search_query = {
        'text': query,
        'page': int(request.params.get('page', 1)),
        'facet': True
    }
    sort = _get_sort()
    facets = _get_facets()
    if sort:
        search_query['sort'] = sort
    if facets:
        search_query['fq'] = facets
    list_visuals_searched = toolkit.get_action(
        'search_visualizations')(
            context,
            search_query)
    visuals = []
    for vis in list_visuals_searched['results']:
        visual = model.Session.query(ResourceView)\
            .get(vis['id'])
        try:
            data_dict_format = model_dictize\
                .resource_view_list_dictize([visual], _get_context())
            visuals.append(data_dict_format[0])
        except Exception as e:
            log.exception(e)

    list_visuals_searched['results'] = visuals
    list_visuals_searched['pager'] = _get_pager(list_visuals_searched,
                                                'visualizations')

    c.search_facets = list_visuals_searched['search_facets']
    return list_visuals_searched


def dashboard_research_questions(context, dashboard):
    questions = []
    indicators = dashboard.get('indicators')
    if indicators:
        if not context:
            context = _get_context()
        research_question_show = logic.get_action('research_question_show')
        if not isinstance(indicators, list):
            indicators = json.loads(indicators)
        for indicator in list(indicators):
            if indicator.get('research_question'):
                try:
                    question = research_question_show(context, {
                        'id': indicator['research_question']
                    })
                    questions.append(question)
                except Exception as e:
                    log.warning('Cannot access reserch question %s. Error: %s',
                                indicator.get('research_question'), str(e))
                    log.exception(e)

    return questions


def add_rqs_to_dataset(context, res_view):

    if not context:
        context = _get_context()
    pkg_dict = toolkit.get_action('package_show')(
        dict({'ignore_auth': True}, return_type='dict'),
        {'id': res_view['package_id']})

    rq_options = get_rq_options(context)
    all_rqs = []
    if not pkg_dict.get('research_question'):
        pkg_dict['research_question'] = []
    else:
        if isinstance(pkg_dict['research_question'], unicode):
            old_rqs = pkg_dict.get('research_question')
            old_list = old_rqs.split(',')

            for old in old_list:
                all_rqs.append(old)
    if res_view.get('research_questions'):
        res_rq = json.loads(res_view.get('research_questions'))
        if isinstance(res_rq, unicode):
            all_rqs.append(res_rq)
        else:
            for new in res_rq:
                all_rqs.append(new)

    eliminate_duplicates = set(all_rqs)
    all_rqs = list(eliminate_duplicates)
    pkg_dict['research_question'] = ",".join(all_rqs)
    try:
        context['defer_commit'] = True
        context['use_cache'] = False
        toolkit.get_action('package_update')(context, pkg_dict)
        context.pop('defer_commit')
    except logic.ValidationError as e:
        try:
            raise logic.ValidationError(e.error_dict['research_question'][-1])
        except (KeyError, IndexError):
            raise logic.ValidationError(e.error_dict)


def remove_rqs_from_dataset(res_view):

    context = _get_context()
    pkg_id = res_view.get('package_id')
    if res_view.get('__extras'):
        ext = res_view.get('__extras')
        if ext.get('research_questions'):
            list_rqs = res_view['__extras']['research_questions']
            data_dict = {}
            should_stay = {}
            for rq in list_rqs:
                data_dict['text'] = rq
                data_dict['fq'] = "khe_package_id:" + pkg_id
                should_stay[rq] = False
                results_search = toolkit.get_action(
                    'search_visualizations')(context, data_dict)
                for res in results_search['results']:
                    if res.get('research_questions') and \
                       res.get('id') != res_view.get('id') and \
                       res.get('khe_package_id') == pkg_id:
                        questions = json.loads(res.get('research_questions'))
                        for q in questions:
                            if q == rq:
                                should_stay[rq] = True
            new_rqs_package_dict = {}
            package_sh = toolkit.get_action('package_show')(
                dict({'ignore_auth': True}, return_type='dict'),
                {'id': pkg_id})
            if package_sh.get('research_question'):
                questions_package = package_sh.get(
                    'research_question').split(",")
                for q in questions_package:
                    if q in should_stay:
                        if not should_stay[q]:
                            questions_package.remove(q)
                package_sh['research_question'] = ",".join(questions_package)

            try:
                context['defer_commit'] = True
                context['use_cache'] = False
                toolkit.get_action('package_update')(context, package_sh)
                context.pop('defer_commit')
                return {"message": _('OK')}
            except ValidationError as e:
                try:
                    raise ValidationError(
                        e.error_dict['research_question'][-1])
                except (KeyError, IndexError):
                    raise ValidationError(e.error_dict)


def update_rqs_in_dataset(old_data, res_view):

    context = _get_context()
    context['ignore_auth'] = True
    pkg_dict = toolkit.get_action('package_show')(
        dict({'ignore_auth': True}, return_type='dict'),
        {'id': res_view['package_id']})

    rq_options = get_rq_options(context)
    all_rqs = []
    if not pkg_dict.get('research_question'):  # dataset has no rqs
        pkg_dict['research_question'] = []
    else:
        if isinstance(pkg_dict['research_question'], unicode):
            # expected format
            old_rqs = pkg_dict.get('research_question')
            old_list = old_rqs.split(',')

            for old in old_list:
                all_rqs.append(old)
    if res_view.get('research_questions'):
        res_rq = json.loads(res_view.get('research_questions'))
        if isinstance(res_rq, list):
            for new in res_rq:
                all_rqs.append(new)
        else:
            all_rqs.append(res_rq)

    eliminate_duplicates = set(all_rqs)
    all_rqs = list(eliminate_duplicates)

    pkg_id = res_view.get('package_id')

    if old_data.get('__extras') and res_view.get('__extras'):
        new_ext = res_view.get('__extras')
        old_ext = old_data.get('__extras')
        list_rqs = []  # list of rqs that were removed in update
        if old_ext.get('research_questions'):  # alrdy had rqs
            if new_ext.get('research_questions'):  # and we have new rqs
                if isinstance(new_ext.get('research_questions'), list):
                    set_new = set(new_ext.get('research_questions'))
                else:  # only one new
                    li = []
                    li.append(new_ext.get('research_questions'))
                    set_new = set(li)
                if isinstance(old_ext.get('research_questions'), list):
                    set_old = set(old_ext.get('research_questions'))
                else:  # only one old
                    li = []
                    li.append(old_ext.get('research_questions'))
                    set_old = set(li)
                list_rqs = list(set_old-set_new)
            else:  # all were removed
                if isinstance(old_ext.get('research_questions'), list):
                    # if they are more than 1
                    list_rqs = old_ext.get('research_questions')
                else:  # if it is only 1
                    list_rqs.append(old_ext.get('research_questions'))
        data_dict = {}
        should_stay = {}
        for rq in list_rqs:
            data_dict['text'] = rq
            data_dict['fq'] = "khe_package_id:" + pkg_id
            should_stay[rq] = False
            results_search = toolkit.get_action(
                'search_visualizations')(context, data_dict)
            for res in results_search['results']:
                if res.get('research_questions'):
                    questions = json.loads(res.get('research_questions'))
                    if isinstance(questions, list):
                        for q in questions:
                            if q == rq:
                                should_stay[rq] = True
                    else:
                        if questions == rq:
                            should_stay[rq] = True
        new_rqs_package_dict = {}

        questions_package = all_rqs
        for q in questions_package:
            if q in should_stay:
                if not should_stay[q]:
                    questions_package.remove(q)
        pkg_dict['research_question'] = ",".join(questions_package)

        try:
            context['defer_commit'] = True
            context['use_cache'] = False
            toolkit.get_action('package_update')(context, pkg_dict)
            context.pop('defer_commit')
        except ValidationError as e:
            try:
                raise ValidationError(e.error_dict['research_question'][-1])
            except (KeyError, IndexError):
                raise ValidationError(e.error_dict)


def get_single_dash(data_dict):
    single_dash = toolkit.get_action('dashboard_show')(
        _get_context(),
        {'id': data_dict.get('id')} if data_dict.get('id')
        else {'name': data_dict.get('name')}
    )
    return single_dash


def is_rsc_upload_datastore(resource):
    u''' Check whether the data resource is uploaded to the Datastore

    The status complete means that data is completely uploaded to Datastore.

    :param resource: data resource dictionary
    :type resource: dict

    :returns: True if uploding is completed otherwise False
    :rtyep: bool
    '''
    context = {'ignore_auth': True}

    try:
        task = toolkit.get_action('task_status_show')(context, {
            'entity_id': resource['id'],
            'task_type': 'datapusher',
            'key': 'datapusher'
        })
        return True if task.get('state') == 'complete' else False
    except logic.NotFound:
        log.debug(
            u'Resource {} not uploaded to datastore!'.format(resource['id'])
        )
    except Exception as e:
        log.debug(u'Task status show: {}'.format(str(e)))

    return False


def get_resource_filtered_data(id):
    u''' Get all data from datastore and exclude `_id` and _full_text`
    from fiedls and records.

    :param id: resource ID
    :type id: string

    :returns: the resource dict with filtered fields and records
    :rtype: dict
    '''
    result = {
        'fields': [],
        'records': []
    }
    try:
        sql = 'SELECT * FROM "{resource}"'.format(resource=id)
        result = toolkit.get_action('datastore_search_sql')(
            {'ignore_auth': True},
            {'sql': sql}
        )
    except Exception as e:
        log.debug(u'Datastore search sql: {}'.format(str(e)))

    if len(result.get('records', [])):
        result['fields'] = [f for f in result['fields']
                            if f['id'] not in INVALID_COLUMN_NAMES]

        filtered_records = []
        for r in result.get('records'):
            row = {k: v for k, v in r.items() if k not in INVALID_COLUMN_NAMES}
            filtered_records.append(row)

        result['records'] = filtered_records

    return result


def get_dataset_data(id):
    u''' Return fields and records from all data resources for given package ID

    The method does not return the data from the system merged data resource.
    If the format of the data resources is different it sets the message that
    tells which resource and what fields are different.

    :param id: the dataset ID
    :type id: string

    :returns: dict with filterd fields and records, package_name, err_msg
    and system_resource
    :rtype: dict
    '''
    data_dict = {
        'fields': [],
        'records': [],
        'package_name': '',
        'err_msg': '',
        'system_resource': {}
    }

    package = toolkit.get_action('package_show')(
        {'ignore_auth': True}, {'id': id})
    data_dict['package_name'] = package.get('name')

    resources = package.get('resources', [])
    if len(resources):
        for resource in resources:
            if resource.get('resource_type') == SYSTEM_RESOURCE_TYPE:
                data_dict['system_resource'] = resource
                continue

            result = get_resource_filtered_data(resource.get('id'))

            if len(result.get('records')):
                if len(data_dict['fields']) == 0:
                    data_dict['fields'] = result['fields']
                    data_dict['records'] = result['records']
                    continue

                if data_dict['fields'] == result.get('fields'):
                    data_dict['records'].extend(result.get('records'))
                else:
                    diff = [f['id'] for f in result.get('fields')
                            if f not in data_dict['fields']]
                    diff.extend([f['id'] for f in data_dict['fields']
                                 if f not in result.get('fields')])
                    data_dict['err_msg'] = ('The format of the data resource '
                                            '{resource} differs from the '
                                            'others, fields: {fields}').format(
                                                resource=resource.get('name'),
                                                fields=", ".join(diff)
                    )
                    break

    return data_dict


def get_package_data_quality(id):
    context = _get_context()
    try:
        result = toolkit.get_action(
            'package_data_quality')(context, {'id': id})
    except Exception:
        return {}
    return result


def get_resource_data_quality(id):
    context = _get_context()
    try:
        result = toolkit.get_action(
            'resource_data_quality')(context, {'id': id})
    except Exception:
        return {}
    return result


def get_resource_validation_data(id):
    context = _get_context()
    try:
        result = toolkit.get_action('resource_validate_status')(
                                    context, {'id': id})
    except Exception:
        return {}
    return result


def views_dashboards_groups_update(package_id):
    ''' Update groups of the visualizations and dashboards

    param package_id: the id or name of the package
    type package_id: string
    '''
    package = toolkit.get_action('package_show')(
        {'ignore_auth': True},
        {'id': package_id, 'include_tracking': True}
    )

    resource_views = []
    for resource in package.get('resources'):
        resource_view_list = toolkit.get_action('resource_view_list')(
            {'ignore_auth': True}, {'id': resource.get('id')})
        for resource_view in resource_view_list:
            if resource_view.get('view_type') == 'chart' or \
               resource_view.get('view_type') == 'map' or \
               resource_view.get('view_type') == 'table':
                resource_views.append(resource_view)

    for view in resource_views:
        view_data = {
            'id': view.get('id'),
            'resource_id': view.get('resource_id'),
            'title': view.get('title'),
            'description': view.get('description'),
            'view_type': view.get('view_type')
        }
        view_data.update(view.get('__extras', {}))
        toolkit.get_action('resource_view_update')(
            {'ignore_auth': True},
            view_data
        )

    for view in resource_views:
        docs = toolkit.get_action('search_dashboards')(
            {'ignore_auth': True},
            {'text': '*', 'fq': 'khe_indicators:' + view.get('id')}
        )

        for dashboard in docs.get('results', []):
            data_dict = toolkit.get_action('dashboard_show')(
                {'ignore_auth': True},
                {'id': dashboard.get('id')}
            )
            toolkit.get_action('dashboard_update')(
                {'ignore_auth': True},
                data_dict
            )


def keyword_list():
    '''Return a list of all keywords

    :returns: the list of all keywords
    :rtype: string
    '''

    return toolkit.get_action('keyword_list')({'ignore_auth': True}, {})


def check_user_profile_preferences():
    u'''Checks if the user has been notified to set his preferences and if not,
    it redirects the user to the User -> Profile page to set his preferences
    and interests.
    '''
    path = request.path
    ignore_patterns = [
        r'^/api.*$',
        r'^.*\.(js|css|png|jpg|jpeg|gif|mp4)',
        r'^/user/profile/save_interests$',
        r'^/user/profile/set_interests$',
        r'^/error.*$',
    ]
    for pattern in ignore_patterns:
        if re.match(pattern, path, re.IGNORECASE):
            return

    username = request.environ.get(u'REMOTE_USER', u'')
    if not username:
        return

    already_checked = request.environ.get(u'__khb_user_pref_checked', False)
    if already_checked:
        return

    user = model.User.by_name(username)
    if not user:
        return

    try:
        profile = toolkit.get_action('user_profile_show')({
            'ignore_auth': True,
            'auth_user_obj': user,
        }, {
            'id': user.id,
        })
    except logic.NotFound:
        profile = toolkit.get_action('user_profile_create')({
            'user': username,
        }, {})

    request.environ['__khb_user_pref_checked'] = True
    if profile.get('user_notified'):
        return

    if is_flask_request():
        from flask import redirect
        url = h.url_for('/user/profile/set_interests')
        response = redirect(url, 302)
        return response
    return toolkit.redirect_to('/user/profile/set_interests')


def get_datasets():
    datasets = toolkit.get_action('package_search')(
        _get_context(),
        {'include_private': True}
    )

    return datasets


def get_notifications(offset=0, limit=10):
    context = _get_context()
    notifications = toolkit.get_action('notification_list')(
        context,
        {
            'offset': offset,
            'limit': limit,
        }
    )
    if notifications.get('count', 0) > offset + limit + 1:
        notifications['has_more'] = True

    return notifications


def get_all_users():
    '''Return the list of user dictionaties(name, display_name)'''

    users_all_fields = toolkit.get_action('user_list')(
        {'ignore_auth': True},
        {'all_fields': True}
    )
    sysadmins = [
        sysadmin.name for sysadmin in get_sysadmins()]

    users = []
    for user in users_all_fields:
        if user.get('name') not in sysadmins:
            users.append(
                {
                    'id': user.get('id'),
                    'name': user.get('name'),
                    'display_name': user.get('fullname') or user.get('name')
                }
            )

    return users


class Permission(Enum):
    Granted = 'Permission granted'
    Revoked = 'Permission revoked'


class Entity(Enum):
    Dataset = 'dataset'
    Dashboard = 'dashboard'
    Resource = 'resource'


def shared_with_users_notification(editor_obj, users, data, entity, perm):
    ''' Send notification to the users to which permission is granted or
    revoked on dataset/dashboard.
    :param editor_obj: the user object of the editor
    :type editor_obj: ckan.model.User
    :param users: a list of user name or ID
    :type users: list
    :param data: a dictionary(at least title and name) of Dataset or Dashboard
    :type data: dict
    :param entity: enumeration, can be Entity.Dataset or Entity.Dashboard
    :type entity: enumeration
    :param perm: enumeration, can be Permission.Granted or Permission.Revoked
    :type perm: enumeration
    '''
    for u in users:
        try:
            user = toolkit.get_action('user_show')(
                {'ignore_auth': True}, {'id': u})
        except logic.NotFound:
            continue

        who = editor_obj.fullname or editor_obj.name
        data_dict = {
            'title': perm.value,
            'recepient': user['id'],
            'description': (
                '%s on %s %s from user %s'
                % (perm.value, entity.value, data.get('title'), who))
        }
        if entity == Entity.Dataset:
            data_dict['link'] = h.url_for('dataset_read', controller='package',
                                          action='read', id=data.get('name'))

        elif entity == Entity.Dashboard:
            data_dict['link'] = h.url_for(
                'dashboards.view', name=data.get('name'))
        else:
            continue

        try:
            toolkit.get_action('notification_create')(
                {'ignore_auth': True}, data_dict)
        except Exception as e:
            log.debug('Unable to send notification: %s' % str(e))


def get_all_organizations():
    return toolkit.get_action('get_all_organizations')(
        {'ignore_auth': True}, {})


def get_all_groups():
    return toolkit.get_action('get_all_groups')({'ignore_auth': True}, {})


def resource_validation_notification(editor_obj, data, entity):
    validation_user = None
    try:
        validation_user = toolkit.get_action('user_show')(
            {'ignore_auth': True}, {'id': data.get('admin')})
    except Exception as e:
        log.debug('Unable to find the user: %s' % str(e))

    who = editor_obj.fullname or editor_obj.name
    if validation_user:
        data_dict = {
            'title': 'Resource Validation',
            'recepient': validation_user['id'],
            'description': (
                'You have been asked to validate a data resource from %s'
                % (who))
        }

    if entity == Entity.Resource:
        context = _get_context()
        resource_name = data['name']
        dataset = toolkit.get_action('package_show')(
            context,
            {u'id': data.get('package_id')}
        )
        resources = dataset.get('resources')
        resource_id = None
        for resource in resources:
            rsc_name = resource.get('name')
            if rsc_name == resource_name:
                resource_id = resource['id']

        data_dict['link'] = h.url_for(
            controller='package',
            action='resource_read',
            id=dataset.get('id'),
            resource_id=resource_id,
            qualified=True
        )

    try:
        toolkit.get_action('notification_create')(
            {'ignore_auth': True}, data_dict)
    except Exception as e:
        log.debug('Unable to send notification: %s' % str(e))


def notification_broadcast(context, notification, orgs_or_groups):

    sender = context.get('auth_user_obj')

    def _send_notification(notification, user_id):
        send_notif = {}
        send_notif.update(notification)
        send_notif['recepient'] = user_id

        try:
            toolkit.get_action('notification_create')(context, send_notif)
        except Exception as e:
            log.warning('Failed to send notification to user: %s. Error: %s',
                        user_id, str(e))
            log.exception(e)

    users = set()
    for group_id in orgs_or_groups:
        members = get_members(context, group_id)
        if members:
            for user_id, _, _ in members:
                if sender and sender.id == user_id:
                    continue
                users.add(user_id)

    log.debug('Broadcasting message to %d users.', len(users))
    for user_id in users:
        _send_notification(notification, user_id)
    log.debug('Notifications sent.')


def get_members(context, group_id):
    try:
        return toolkit.get_action('member_list')(context, {
            'id': group_id,
            'object_type': 'user',
        })
    except Exception as e:
        log.warning('Failed to get members list for group %s. Error: %s',
                    group_id, str(e))
        log.exception(e)
    return []


def check_if_dataset_is_on_hdx(dataset_name):
    try:
        dataset = Dataset.read_from_hdx(dataset_name)
        if not dataset:
            return False
        return True
    except Exception as e:
        log.debug('Failed to read from HDX. Error: %s', str(e))
        log.exception(e)
    return False


def human_elapsed_time(dt):
    now = datetime.utcnow()
    if isinstance(dt, str) or isinstance(dt, unicode):
        dt = parser.parse(dt)
    return humanize.naturaltime(now - dt)


def get_requested_resource_type_and_ref():
    if 'pylons.original_request' in request.environ:
        path = request.environ['pylons.original_request'].path_qs
    else:
        path = request.path

    if not path:
        return None

    patterns = {
        'dataset': r'^/dataset/(?P<ref>[^/]+)$',
        'dashboard': r'^/dashboards/(?P<ref>[^/]+)/view$',
        'visualization':
            r'^/dataset/[^/]+/resource/[^/]+$\?view_id=(?P<ref>[a-f0-9\-]+)',
    }

    for entity_type, pattern in patterns.items():
        match = re.match(pattern, path)
        if match:
            entity_ref = match.group('ref')
            return {
                'entity_type': entity_type,
                'entity_ref': entity_ref,
            }

    return None


def get_comments_count(ref):
    '''Returns the total number of comments for this entity identified by
    its reference (`ref`).

    :param ref: `str`, the reference to the entity.

    :returns: `int`, total number of comments (including replies).
    '''
    return Comment.get_comments_count(ref) or 0


def tag_mentions(text):
    '''Tags the given text with mentions.

    Parses the text to locate potential mentions. A mention starts with `@` and
    is followed by a name of a user, group or organization. For example:
    `@user-a`, `@group-b`, `@some_other_user` etc.
    The name must not contain a white space, it can contain alpha-numeric
    characters and underscore (`_`) or minus sign (`-`).

    The list of extracted mentions is then resolved to find out which of those
    are actual names of users, groups or organizations.
    The valid (resolved) mentions are then processed and replaced in the text
    with markdown markup for link. For example:

        This mention of @john-smith-02 is an example.

    will be converted to:

        This mention of [@John Smith](/users/john-smith-02) is an example.

    The mention is replaced by the markdown representation of the mention using
    the real name (display name in case of a user or title for org/group) and
    a link to the user profile or a link to the organization.

    This helper returns the processed text and a list of the valid (resolved)
    mentions.

    :param text: `str`, the text to parse and tag.

    :returns: `str` the tagged text and a `list` of resolved mentions.
    '''
    mentions = []

    for m in re.finditer(r'@([a-zA-Z0-9_.@-]+)', text):
        if m:
            mentions.append((m.group(1), m.start(), m.end()))

    resolved = toolkit.get_action('resolve_mentions')({
        'ignore_auth': True,
    }, {
        'mentions': [m[0] for m in mentions],
    })

    resolved_mentions = []
    tagged_text = ''
    pos = 0
    for mention, start, end in mentions:
        tagged_text += text[pos:start]
        res_mention = resolved.get(mention)
        if res_mention:
            tagged_text += '[@{}]({})'.format(
                res_mention['label'],
                res_mention['link']
            )
            resolved_mentions.append(res_mention)
        else:
            tagged_text += '@' + mention
        pos = end

    tagged_text += text[pos:]

    return (tagged_text, resolved_mentions)


def generate_ref_type_url(ref_type, ref):
    '''Generates a URL reference to the object with given type and ID.

    :param ref_type: `str`, type of object: `dataset`, `resource`, `post` etc
    :param ref: `str`, the reference to the object (ID or name).

    :returns: `str`, the URL for that object on the site.
    '''
    def _post_url():
        return h.url_for('news.view', id=ref)

    def _dataset_url():
        return h.url_for('dataset_read', controller='package',
                         action='read', id=ref)

    def _dashboard_url():
        return h.url_for('dashboards.view', name=ref)

    def _visualization_url():
        try:
            visualization = toolkit.get_action('resource_view_show')({
                'ignore_auth': True,
            }, {
                'id': ref,
            })
            return h.url_for(controller='package',
                             action='resource_read',
                             id=visualization['package_id'],
                             resource_id=visualization['resource_id'],
                             view_id=visualization['id'])
        except Exception as e:
            log.exception(e)
            return h.url_for('/')

    generators = {
        'post': _post_url,
        'dataset': _dataset_url,
        'dashboard': _dashboard_url,
        'visualization': _visualization_url,
    }
    if ref_type not in generators:
        raise ValidationError({'ref_type': [_('Invalid value')]})

    return generators[ref_type]()


def get_countries():
    ''' Returns list of all countries
    '''

    return pycountry.countries


def _ignore_path(path):
    if not path:
        return True
    ignore_paths = [
        '.css', '.js',
        '.png', '.jpg', '.jpeg', '.gif', '.webp',
        '.mp4', '.mp3', '.mov', '.mtr', '.ogg', '.oga', '.ogv', '.webm',
        '/api/i18n/en',
    ]

    path = path.lower()
    for ext in ignore_paths:
        if path.endswith(ext):
            return True
    return False


def log_request():
    session_id = None
    try:
        session_id = request.environ.get('beaker.session').id
    except Exception as e:
        log.debug(e)
        log.exception(e)

    if _ignore_path(request.path):
        return

    user_agent_string = request.environ.get('HTTP_USER_AGENT')
    client_os = None
    client_device = None
    if user_agent_string:
        try:
            user_agent = UserAgent(user_agent_string)
            client_os = user_agent.platform
            client_device = user_agent.browser
        except Exception as e:
            log.debug(e)

    # try:
    #     print 'Request Headers: ', request.headers
    # except Exception as e:
    #     log.exception(e)

    # try:
    #     print 'Request Environ: ', json.dumps(request.environ, indent=2, default=str)
    # except Exception as e:
    #     log.exception(e)
    
    remote_ip = ''
    # Try in X-Forwarded-For and related HTTP headers
    for header in ['X-Forwarded-For', 'X-ProxyUser-Ip', 'X-Real-Ip']:
        try:
            x_fwd = request.headers.get(header)
            if x_fwd:
                x_fwd = x_fwd.split(',')
                if x_fwd and x_fwd[0]:
                    x_fwd = x_fwd[0].strip()
                    if re.match(r'^\d+(\.\d+){3}(\:\d)?$', x_fwd):
                        # IPv4
                        if ':' in x_fwd:
                            remote_ip = x_fwd.split(':')[0]
                        else:
                            remote_ip = x_fwd
                    else:
                        # IPv6
                        remote_ip = x_fwd
        except Exception as e:
            log.debug('Failed to get REMOTE IP while examining header: %s',
                      header)
            log.exception(e)

    if not remote_ip:
        remote_ip = request.environ.get('REMOTE_ADDR')

    data = {
        'remote_ip': remote_ip,
        'remote_user': request.environ.get('REMOTE_USER'),
        'session': session_id,
        'current_language': request.environ.get('CKAN_LANG'),
        'access_time': datetime.now(),
        'request_url': request.environ.get('CKAN_CURRENT_URL'),
        'http_method': request.environ.get('REQUEST_METHOD'),
        'http_path': request.path,
        'http_query_params': request.environ.get('QUERY_STRING'),
        'http_user_agent': user_agent_string,
        'client_os': client_os,
        'client_device': client_device
    }

    get_request_audit().log(data)
