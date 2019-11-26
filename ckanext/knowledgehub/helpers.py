import logging
import os
import pkgutil
import inspect
import uuid
import json
import functools32
import requests
from datetime import datetime
from flask import Blueprint

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

import ckan.plugins.toolkit as toolkit
import ckan.model as model
from ckan.common import g, _
from ckan import logic
from ckan.model import ResourceView, Resource
from ckan import lib
from ckan.controllers.admin import get_sysadmins

from ckanext.knowledgehub.model import Dashboard
from ckanext.knowledgehub.rnn import helpers as rnn_helpers


log = logging.getLogger(__name__)
model_dictize = lib.dictization.model_dictize


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


def get_rq_options(idValue=False):
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
    return data_dict_format


def get_rqs_dashboards(rq_tit):

    visualizations = toolkit.get_action('dashboards_for_rq')(_get_context(), {
                        'research_question': rq_tit
                    })

    return(visualizations)


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
    data = {
        'query': 'format:geojson',
        'order_by': 'name',
    }
    result = toolkit.get_action('resource_search')(context, data)
    return [{'text': r['name'], 'value': r['url']}
            for r in result.get('results', [])]


def get_dataset_url_path(url):
    # Remove http://host:port/lang part
    parts = url.split('/dataset')
    if len(parts) == 1:
        return ''
    return '/dataset%s' % parts[1]


def get_map_data(geojson_url, map_key_field, data_key_field,
                 data_value_field, from_where_clause):

    geojson_keys = []
    resp = requests.get(geojson_url)
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


def get_geojson_properties(url):
    # TODO handle if no url
    # TODO handle topojson format
    resp = requests.get(url)
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


def get_dashboards(limit=5, order_by='created_by asc'):
    dashboards = Dashboard.search(limit=limit, order_by=order_by).all()

    return dashboards


def remove_space_for_url(str):
    return str.replace(" ", "-")

def format_date(str):
    # split date & time
    date = str.split('T') # date[0] is the date, date[1] is the time
    time_basic = date[1].split('.') # time_basic[0] = hh/mm/ss
    # remove seconds 
    time_basic[0] = time_basic[0][:-3]
    display_date = date[0] + ' at ' + time_basic[0]
    return display_date
