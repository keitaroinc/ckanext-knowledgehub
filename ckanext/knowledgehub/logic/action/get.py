import logging
import re
import os
import json
from six import string_types, iteritems

from paste.deploy.converters import asbool

import ckan.logic as logic
from ckan.logic.action.get import package_search as ckan_package_search
from ckan.plugins import toolkit
from ckan.common import _, config, json
from ckan import lib
from ckan import model
from ckan.model.meta import Session
from ckanext.knowledgehub.model import (
    Theme,
    SubThemes,
    ResearchQuestion,
    Dashboard,
    ResourceFeedbacks,
    ResourceValidate,
    KWHData,
    RNNCorpus,
    Visualization,
    UserIntents,
    UserQuery,
    UserQueryResult, DataQualityMetrics,
    Keyword,
    ExtendedTag,
    UserProfile,
    Notification
)
from ckanext.knowledgehub import helpers as kh_helpers
from ckanext.knowledgehub.lib.rnn import PredictiveSearchModel
from ckanext.knowledgehub.lib.solr import ckan_params_to_solr_args
from ckan.lib import helpers as h
from ckan.controllers.admin import get_sysadmins

from ckanext.knowledgehub.backend.factory import get_backend
from ckanext.knowledgehub.lib.writer import WriterService

from hdx.utilities.easy_logging import setup_logging
from hdx.hdx_configuration import Configuration
from hdx.data.dataset import Dataset
from hdx.data.organization import Organization
from hdx.data.resource import Resource


log = logging.getLogger(__name__)

_table_dictize = lib.dictization.table_dictize
model_dictize = lib.dictization.model_dictize
misc = model.misc
check_access = toolkit.check_access
NotFound = logic.NotFound
_get_or_bust = logic.get_or_bust
ValidationError = toolkit.ValidationError
NotAuthorized = toolkit.NotAuthorized


class DateTimeEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return (datetime.datetime.min + obj).time().isoformat()

        return super(DateTimeEncoder, self).default(obj)


@toolkit.side_effect_free
def theme_show(context, data_dict):
    '''
        Returns existing analytical framework Theme

    :param id: id of the resource that you
    want to search against.
    :type id: string

    :param name: name of the resource
    that you want to search against. (Optional)
    :type name: string

    :returns: single theme dict
    :rtype: dictionary
    '''
    name_or_id = data_dict.get("id") or data_dict.get("name")

    if name_or_id is None:
        raise ValidationError({'id': _('Missing value')})

    theme = Theme.get(name_or_id)

    if not theme:
        log.debug(u'Could not find theme %s',
                  name_or_id)
        raise NotFound(_(u'Theme was not found.'))

    return _table_dictize(theme, context)


@toolkit.side_effect_free
def theme_list(context, data_dict):
    ''' List themes

    :param page: current page in pagination (optional, default to 1)
    :type page: integer
    :param sort: sorting of the search results.  Optional.  Default:
        "name asc" string of field name and sort-order. The allowed fields are
        'name', and 'title'
    :type sort: string
    :param limit: Limit the search criteria (defaults to 10000).
    :type limit: integer
    :param offset: Offset for the search criteria (defaults to 0).
    :type offset: integer

    :returns: a dictionary including total items,
     page number, items per page and data(themes)
    :rtype: dictionary
    '''

    page = int(data_dict.get(u'page', 1))
    limit = int(data_dict.get(u'limit', 10000))
    offset = int(data_dict.get(u'offset', 0))
    sort = data_dict.get(u'sort', u'name asc')
    q = data_dict.get(u'q', u'')

    themes = []

    t_db_list = Theme.search(q=q,
                             limit=limit,
                             offset=offset,
                             order_by=sort)\
        .all()

    for theme in t_db_list:
        themes.append(_table_dictize(theme, context))

    total = len(Theme.search().all())

    return {u'total': total, u'page': page,
            u'items_per_page': limit, u'data': themes}


@toolkit.side_effect_free
def sub_theme_show(context, data_dict):
    ''' Shows a sub-theme

    :param id: the sub-theme's ID
    :type id: string

    :param name the sub-theme's name
    :type name: string

    :returns: a sub-theme
    :rtype: dictionary
    '''

    id_or_name = data_dict.get('id') or data_dict.get('name')
    if not id_or_name:
        raise ValidationError({u'id': _(u'Missing value')})

    st = SubThemes.get(id_or_name=id_or_name, status='active').first()

    if not st:
        raise NotFound(_(u'Sub-theme'))

    return st.as_dict()


@toolkit.side_effect_free
def sub_theme_list(context, data_dict):
    ''' List sub-themes

    :param page: current page in pagination
     (optional, default: ``1``)
    :type page: int
    :param pageSize: the number of items to
    return (optional, default: ``10000``)
    :type pageSize: int

    :returns: a dictionary including total
    items, page number, page size and data(sub-themes)
    :rtype: dictionary
    '''

    q = data_dict.get('q', '')
    theme = data_dict.get('theme', None)
    page_size = int(data_dict.get('pageSize', 10000))
    page = int(data_dict.get('page', 1))
    order_by = data_dict.get('order_by', 'title asc')
    offset = (page - 1) * page_size
    status = 'active'

    kwargs = {}

    if theme:
        kwargs['theme'] = theme

    kwargs['q'] = q
    kwargs['limit'] = page_size
    kwargs['offset'] = offset
    kwargs['order_by'] = order_by
    kwargs['status'] = status

    st_list = []

    st_db_list = SubThemes.get(**kwargs).all()

    for entry in st_db_list:
        st_list.append(_table_dictize(entry, context))

    total = len(SubThemes.get(**kwargs).all())

    return {'total': total, 'page': page,
            'pageSize': page_size, 'data': st_list}


@toolkit.side_effect_free
def research_question_show(context, data_dict):
    '''Show a single research question.

    :param id: Research question database id
    :type id: string

    :returns: a research question
    :rtype: dictionary
    '''

    id_or_name = data_dict.get('id') or data_dict.get('name')

    if not id_or_name:
        raise ValidationError({u'id': _(u'Missing value')})

    rq = ResearchQuestion.get(id_or_name=id_or_name).first()

    if not rq:
        raise NotFound(_(u'Research question'))
    return rq.as_dict()


@toolkit.side_effect_free
def research_question_list(context, data_dict):
    ''' List research questions

    :param page: current page in pagination
    (optional, default: ``1``)
    :type page: int
    :param pageSize: the number of items
    to return (optional, default: ``10000``)
    :type pageSize: int

    :returns: a dictionary including total
     items, page number, page size and data
    :rtype: dictionary
    '''
    q = data_dict.get('q', '')
    page_size = int(data_dict.get('pageSize', 10000))
    page = int(data_dict.get('page', 1))
    offset = (page - 1) * page_size
    order_by = data_dict.get('order_by', 'name asc')
    rq_list = []

    rq_db_list = ResearchQuestion.get(q=q,
                                      limit=page_size,
                                      offset=offset,
                                      order_by=order_by).all()

    for entry in rq_db_list:
        rq_list.append(_table_dictize(entry, context))

    total = len(ResearchQuestion.get(q=q).all())

    return {'total': total, 'page': page,
            'pageSize': page_size, 'data': rq_list}


@toolkit.side_effect_free
def test_import(context, data_dict):
    # Example how to use backend factory
    backend = get_backend(data_dict)
    backend.configure(data_dict)
    data = backend.search_sql(data_dict)
    # Example how to use csv file writer
    writer = WriterService()
    stream = writer.csv_writer(data.get('fields'),
                               data.get('records'),
                               ',')

    return data


# Overwrite of the original 'resource_view_list'
# action in order to return all existing resource
# views instead just for the appropriate
# view_plugins enabled
def resource_view_list(context, data_dict):
    '''
    Return the list of resource views for a particular resource.

    :param id: the id of the resource
    :type id: string

    :rtype: list of dictionaries.
    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')
    resource = model.Resource.get(id)
    if not resource:
        raise NotFound
    context['resource'] = resource
    # TODO need to implement custom authorization actions
    # check_access('resource_view_list', context, data_dict)
    q = model.Session.query(model.ResourceView).filter_by(resource_id=id)

    resource_views = [
        resource_view for resource_view
        in q.order_by(model.ResourceView.order).all()
    ]
    return model_dictize.resource_view_list_dictize(resource_views, context)


def resource_view_all(context, data_dict):

    q = model.Session.query(model.ResourceView).all()

    resource_view_list = []
    for item in q:
        element = {
            "id": item.id,
            "resource_id": item.resource_id,
            "title": item.title,
            "description": item.description,
            "view_type": item.view_type,
            "order": item.order,
            "config": item.config,
            "tags": item.tags
        }
        resource_view_list.append(element)

    return resource_view_list


@toolkit.side_effect_free
def get_chart_data(context, data_dict):
    '''
    Return the resource data from DataStore.

    :param sql_string: the SQL query that will be executed to get the data.
    :type sql_string: string
    :param category: the selected category
    :type category: string
    :param x_axis: the X axis dimension
    :type x_axis: string
    :param y_axis: the Y axis dimension
    :type y_axis: string
    :param chart_type: the type of the chart
    :type chart_type: string
    :param resource_id: the ID of the resource
    :type resource_id: string

    :rtype: list of dictionaries.
    '''
    category = data_dict.get('category')
    sql_string = data_dict.get('sql_string')
    x_axis = data_dict.get('x_axis')
    y_axis = data_dict.get('y_axis')
    resource_id = data_dict.get('resource_id').strip()
    filters = json.loads(data_dict.get('filters'))
    sql_without_group = sql_string.split('GROUP BY')[0]
    sql_group = sql_string.split('GROUP BY')[1]
    has_where_clause = len(sql_string.split('WHERE')) > 1
    categories_data = {}

    if category:
        x = []
        x.append('x')
        values = []
        static_reference_values = []

        category_values = \
            sorted(kh_helpers.get_filter_values(resource_id,
                                                category,
                                                filters))

        x_axis_values = \
            sorted(kh_helpers.get_filter_values(resource_id,
                                                x_axis,
                                                filters))

        for x_value in x_axis_values:
            categories_data[x_value] = []
            categories_data[x_value].append(x_value)

        for value in category_values:
            # check if there is no
            # value skip querying data
            if not value:
                continue

            if (has_where_clause):
                category_value_sql = sql_without_group + u'AND ("' + \
                    category + u'" = ' + u"'" + value + \
                    u"'" + u') ' + u'GROUP BY' + sql_group
            else:
                category_value_sql = sql_without_group + u'WHERE ("' + \
                    category + u'" = ' + u"'" + value + \
                    u"'" + u') ' + u'GROUP BY' + sql_group

            records = kh_helpers.get_resource_data(category_value_sql)
            x.append(value)

            for record in records:
                value = record[y_axis.lower()]
                categories_data[record[x_axis.lower()]].append(value)
                try:
                    value = float(value)
                    values.append(value)
                except Exception:
                    pass

        if values:
            categories_data['y_axis_max'] = max(values)
            categories_data['y_axis_avg'] = sum(values)/len(values)
            categories_data['y_axis_min'] = min(values)

        categories_data['x'] = x
        return categories_data
    else:
        return kh_helpers.get_resource_data(sql_string)


@toolkit.side_effect_free
def get_resource_data(context, data_dict):
    '''
    Return the resource data from DataStore.

    :param sql_string: the SQL query that will be executed to get the data.
    :type sql_string: string
    '''
    sql_string = data_dict.get('sql_string')
    return kh_helpers.get_resource_data(sql_string)


@toolkit.side_effect_free
def dashboard_show(context, data_dict):
    '''
        Returns existing dashboard

    :param id: id of the dashboard that you
    want to search against.
    :type id: string

    :param name: name of the dashboard
    that you want to search against. (Optional)
    :type name: string

    :returns: single dashboard dict
    :rtype: dictionary
    '''
    check_access('dashboard_show', context, data_dict)

    name_or_id = data_dict.get("id") or data_dict.get("name")

    if name_or_id is None:
        raise ValidationError({'id': _('Missing value')})

    dashboard = Dashboard.get(name_or_id)

    if not dashboard:
        log.debug(u'Could not find dashboard %s',
                  name_or_id)
        raise NotFound(_(u'Dashboard was not found.'))

    return _table_dictize(dashboard, context)


@toolkit.side_effect_free
def dashboard_list(context, data_dict):
    ''' List dashboards

    :param page: current page in pagination (optional, default to 1)
    :type page: integer
    :param sort: sorting of the search results.  Optional.  Default:
        "name asc" string of field name and sort-order. The allowed fields are
        'name', and 'title'
    :type sort: string
    :param limit: Limit the search criteria (defaults to 10000).
    :type limit: integer
    :param offset: Offset for the search criteria (defaults to 0).
    :type offset: integer

    :returns: a dictionary including total items,
     page number, items per page and data(dashboards)
    :rtype: dictionary
    '''

    page = int(data_dict.get(u'page', 1))
    limit = int(data_dict.get(u'limit', 10000))
    offset = int(data_dict.get(u'offset', 0))
    sort = data_dict.get(u'sort', u'name asc')
    q = data_dict.get(u'q', u'')

    def result_iter(limit=100):
        offset = 0
        while True:
            dashboards = Dashboard.search(q=q,
                                          limit=limit,
                                          offset=offset,
                                          order_by=sort).all()
            if not dashboards:
                break
            for dashboard in dashboards:
                yield dashboard
            offset += limit

    dashboards = []
    for dashboard in result_iter():
        try:
            check_access('dashboard_show', context, {'name': dashboard.name})
        except NotAuthorized:
            continue

        if len(dashboards) == limit + offset:
            break

        dashboards.append(_table_dictize(dashboard, context))

    return {u'total': len(Dashboard.search().all()),
            u'page': page,
            u'items_per_page': limit,
            u'data': dashboards[offset:offset+limit]}


@toolkit.side_effect_free
def knowledgehub_get_map_data(context, data_dict):

    geojson_url = data_dict.get('geojson_url')
    map_key_field = data_dict.get('map_key_field')
    data_key_field = data_dict.get('data_key_field')
    data_value_field = data_dict.get('data_value_field')
    from_where_clause = data_dict.get('from_where_clause')

    return kh_helpers.get_map_data(geojson_url, map_key_field, data_key_field,
                                   data_value_field, from_where_clause)


@toolkit.side_effect_free
def knowledgehub_get_geojson_properties(context, data_dict):
    map_resource_url = data_dict.get('map_resource')

    return kh_helpers.get_geojson_properties(map_resource_url)


@toolkit.side_effect_free
def visualizations_for_rq(context, data_dict):
    ''' List visualizations (resource views) based on a research question

    Only resource views of type chart, table and map are considered.

    :param research_question: Title of a research question
    :type research_question: string

    :returns: list of dictionaries, where each dictionary is a resource view
    :rtype: list
    '''
    research_question = data_dict.get('research_question')
    if not research_question:
        raise toolkit.ValidationError(
            'Query parameter `research_question` is required')

    resource_views = []

    datasets = toolkit.get_action('package_search')(context, {
        'fq': '+extras_research_question:{0}'.format(research_question),
        'include_private': True
    })

    for dataset in datasets.get('results'):
        for resource in dataset.get('resources'):
            resource_view_list = toolkit.get_action('resource_view_list')(
                context, {'id': resource.get('id')})
            for resource_view in resource_view_list:
                if resource_view.get('view_type') == 'chart' or \
                   resource_view.get('view_type') == 'map' or \
                   resource_view.get('view_type') == 'table':
                    resource_views.append(resource_view)

    return resource_views


def dashboards_for_rq(context, data_dict):
    research_question = data_dict.get('research_question')

    if not research_question:
        raise toolkit.ValidationError(
            'Query parameter `research_question` is required')

    views = []

    datasets = toolkit.get_action('package_search')(context, {
        'fq': '+extras_research_question:{0}'.format(research_question)
    })

    for dataset in datasets.get('results'):
        for resource in dataset.get('resources'):
            dash_list = toolkit.get_action('dashboard_list')(
                context, {'id': resource.get('id')})
            for res_view in dash_list['data']:
                views.append(res_view)

    return views


@toolkit.side_effect_free
def resource_user_feedback(context, data_dict):
    ''' Returns user's feedback

    :param resource: resource ID
    :type page: string


    :returns: a resource feedback as dictionary
    :rtype: dictionary
    '''
    user = context.get('user')
    user_id = model.User.by_name(user.decode('utf8')).id

    resource = data_dict.get('resource')
    if not resource:
        raise ValidationError({'resource': _('Missing value')})

    rf = ResourceFeedbacks.get(user=user_id, resource=resource).all()
    if not rf:
        raise NotFound(_(u'Resource feedback was not found.'))
    else:
        user_feedbacks = []
        for entry in rf:
            user_feedbacks.append(_table_dictize(entry, context))
        return user_feedbacks


@toolkit.side_effect_free
def resource_feedback_list(context, data_dict):
    ''' List resource feedbacks

    :param page: current page in pagination (optional, default to 1)
    :type page: integer
    :param sort: sorting of the search results.  Optional.  Default:
        "name asc" string of field name and sort-order. The allowed fields are
        'name', and 'title'
    :type sort: string
    :param limit: Limit the search criteria (defaults to 1000000).
    :type limit: integer
    :param offset: Offset for the search criteria (defaults to 0).
    :type offset: integer

    :param type: one of the available resource feedbacks(useful, unuseful,
    trusted, untrusted).
    :type type: string
    :param resource: resource ID
    :type resource: string
    :param dataset: dataset ID
    :type dataset: string

    :returns: a dictionary including total items,
     page number, items per page and data(feedbacks)
    :rtype: dictionary
    '''
    type = data_dict.get('type', '')
    resource = data_dict.get('resource', '')
    dataset = data_dict.get('dataset', '')

    q = data_dict.get('q', '')
    page_size = int(data_dict.get('pageSize', 1000000))
    page = int(data_dict.get('page', 1))
    order_by = data_dict.get('order_by', None)
    offset = (page - 1) * page_size

    kwargs = {}

    if type:
        kwargs['type'] = type
    if resource:
        kwargs['resource'] = resource
    if dataset:
        kwargs['dataset'] = dataset

    kwargs['q'] = q
    kwargs['limit'] = page_size
    kwargs['offset'] = offset
    kwargs['order_by'] = order_by

    rf_list = []

    try:
        rf_db_list = ResourceFeedbacks.get(**kwargs).all()
    except Exception:
        return {'total': 0, 'page': page,
                'pageSize': page_size, 'data': []}

    for entry in rf_db_list:
        rf_list.append(_table_dictize(entry, context))

    total = len(rf_list)

    return {'total': total, 'page': page,
            'pageSize': page_size, 'data': rf_list}


@toolkit.side_effect_free
def get_rq_url(context, data_dict):

    return h.url_for('research_question.read', name=data_dict['name'])


@toolkit.side_effect_free
def kwh_data_list(context, data_dict):
    ''' List KnowledgeHub data
    :param type: origin of the data, one of theme, sub-theme,
        rq and search
    :type type: string
    :param content: the actual data
    :type content: string
    :param user: the user ID
    :type user: string
    :param theme: the theme ID
    :type theme: string
    :param sub_theme: the sub-theme ID
    :type sub_theme: string
    :param rq: the research question ID
    :type rq: string
    :returns: a dictionary including total items,
     page number, items per page and data(KnowledgeHub data)
    :rtype: dictionary
    '''
    data_type = data_dict.get('type', '')
    content = data_dict.get('content', '')
    user = data_dict.get('user', '')
    theme = data_dict.get('theme', '')
    sub_theme = data_dict.get('sub_theme', '')
    rq = data_dict.get('rq', '')

    q = data_dict.get('q', '')
    limit = int(data_dict.get('limit', 1000000))
    page = int(data_dict.get('page', 1))
    order_by = data_dict.get('order_by', None)
    offset = (page - 1) * limit

    kwargs = {}

    if data_type:
        kwargs['type'] = data_type
    if content:
        kwargs['content'] = content
    if user:
        kwargs['user'] = user
    if theme:
        kwargs['theme'] = theme
    if sub_theme:
        kwargs['sub_theme'] = sub_theme
    if rq:
        kwargs['rq'] = rq

    kwargs['q'] = q
    kwargs['limit'] = limit
    kwargs['offset'] = offset
    kwargs['order_by'] = order_by

    kwh_data = []

    try:
        db_data = KWHData.get(**kwargs).all()
    except Exception as e:
        log.debug('Knowledge hub data list: %s' % str(e))
        return {'total': 0, 'page': page,
                'limit': limit, 'data': []}

    for entry in db_data:
        kwh_data.append(_table_dictize(entry, context))

    total = len(kwh_data)

    return {'total': total, 'page': page,
            'limit': limit, 'data': kwh_data}


@toolkit.side_effect_free
def get_last_rnn_corpus(context, data_dict):
    ''' Returns last RNN corpus
    :returns: a RNN corpus
    :rtype: string
    '''

    c = RNNCorpus.get(order_by='created_at desc', limit=1).first()
    if not c:
        raise NotFound(_(u'There is not corpus stored yet!'))
    else:
        return c.corpus


def _get_predictions_from_db(query):
    number_predictions = int(
        config.get(
            u'ckanext.knowledgehub.rnn.number_predictions',
            3
        )
    )

    text = ' '.join(query.split()[-3:])
    data_dict = {
        'q': text,
        'limit': 10,
        'order_by': 'created_at desc'
    }
    kwh_data = toolkit.get_action('kwh_data_list')({}, data_dict)

    def _get_predict(text, query, index):
        predict = ''
        if index != -1:
            index = index + len(query)
            for i, ch in enumerate(text[index:]):
                if ch.isalnum() or (i == 0 and ch == ' '):
                    predict += ch
                else:
                    break

        return predict

    def _findall(pattern, text):
        return [
            match.start(0) for match in re.finditer(pattern, text)
        ]

    predictions = []
    for data in kwh_data.get('data', []):
        if len(predictions) >= number_predictions:
            break

        title = data.get('title').lower()
        for index in _findall(query, title):
            predict = _get_predict(title, query, index)
            if predict != '' and predict not in predictions:
                predictions.append(predict)

        if data.get('description'):
            description = data.get('description').lower()
            for index in _findall(query, description):
                predict = _get_predict(description, query, index)
                if predict != '' and predict not in predictions:
                    predictions.append(predict)

    return predictions[:number_predictions]


@toolkit.side_effect_free
def get_predictions(context, data_dict):
    ''' Returns a list of predictions from RNN model and DB based
    on data store in knowledge hub

    :param query: the search query for which predictions have to be made
    :type query: string
    :returns: predictions
    :rtype: list
    '''
    query = data_dict.get('query')
    if not query:
        raise ValidationError({'query': _('Missing value')})
    if len(query) < int(config.get(
            u'ckanext.knowledgehub.rnn.sequence_length', 10)):
        return []

    if query.isspace():
        return []
    query = query.lower()

    predictions = _get_predictions_from_db(query)

    model = PredictiveSearchModel()
    for p in model.predict(query):
        if p not in predictions:
            predictions.append(p)

    return predictions


def _search_entity(index, ctx, data_dict):
    model = ctx['model']
    session = ctx['session']

    page = data_dict.get('page', 1)
    page_size = int(data_dict.get('limit',
                                  config.get('ckan.datasets_per_page', 20)))
    if page <= 0:
        page = 1

    # clean the data dict
    for k in ['page', 'limit']:
        if data_dict.get(k) is not None:
            del data_dict[k]

    data_dict['rows'] = page_size
    data_dict['start'] = (page - 1) * page_size

    text = data_dict.get('text')
    if not text:
        raise ValidationError({'text': _('Missing value')})

    _save_user_query(ctx, text, index.doctype)

    args = ckan_params_to_solr_args(data_dict)

    if ctx.get('auth_user_obj'):
        args['boost_for'] = ctx['auth_user_obj'].id

    results = index.search_index(**args)

    results.page = page
    results.page_size = page_size

    # get facets and convert facets list to a dict
    facets = results.facets.get('facet_fields', {})
    for field, values in iteritems(facets):
        facets[field] = dict(zip(values[0::2], values[1::2]))

    group_names = []
    for field_name in ('groups', 'organizations'):
        group_names.extend(facets.get(field_name, {}).keys())

    groups = (session.query(model.Group.name, model.Group.title)
              .filter(model.Group.name.in_(group_names))
              .all()
              if group_names else [])
    group_titles_by_name = dict(groups)

    result_dict = {
        'count': results.hits,
        'results': results.docs,
        'facets': facets,
        'search_facets': _restructured_facets(facets, group_titles_by_name),
        'stats': results.stats,
        'page': page,
        'limit': page_size,
    }

    class _results_wrapper(dict):
        def _for_json(self):
            return json.dumps(self, cls=DateTimeEncoder)

    return _results_wrapper(result_dict)


def _restructured_facets(facets, group_titles_by_name):
    restructured_facets = {}
    for key, value in facets.items():
        restructured_facets[key] = {
            'title': key,
            'items': []
        }
        for key_, value_ in value.items():
            if value_ == 0:
                continue
            new_facet_dict = {}
            new_facet_dict['name'] = key_
            if key in ('groups', 'organizations'):
                display_name = group_titles_by_name.get(key_, key_)
                if display_name and display_name.strip():
                    display_name = display_name
                else:
                    display_name = key_
                new_facet_dict['display_name'] = display_name
            else:
                new_facet_dict['display_name'] = key_
            new_facet_dict['count'] = value_
            restructured_facets[key]['items'].append(new_facet_dict)

    for facet in restructured_facets:
        restructured_facets[facet]['items'] = sorted(
            restructured_facets[facet]['items'],
            key=lambda facet: facet['display_name'], reverse=True)

    return restructured_facets


def _save_user_query(ctx, text, doc_type):
    ctx['ignore_auth'] = True

    if text != '*':
        query_data = {
            'query_text': text,
            'query_type': doc_type
        }
        try:
            logic.get_action('user_query_create')(ctx, query_data)
        except Exception as e:
            log.debug('Save user query: %s', str(e))


@toolkit.side_effect_free
def search_dashboards(context, data_dict):
    u'''Performs a search in the index for dashboards.

    :param data_dict: ``dict``, the query arguments for the search.

    :returns: ``list``, the documents matching the search query from the index.
    '''
    return _search_entity(Dashboard, context, data_dict)


@toolkit.side_effect_free
def search_research_questions(context, data_dict):
    u'''Performs a search in the index for research questions.

    :param data_dict: ``dict``, the query arguments for the search.

    :returns: ``list``, the documents matching the search query from the index.
    '''
    return _search_entity(ResearchQuestion, context, data_dict)


@toolkit.side_effect_free
def search_visualizations(context, data_dict):
    u'''Performs a search in the index for visualizations.

    :param data_dict: ``dict``, the query arguments for the search.

    :returns: ``list``, the documents matching the search query from the index.
    '''
    return _search_entity(Visualization, context, data_dict)


@toolkit.side_effect_free
def user_intent_list(context, data_dict):
    ''' List the users intents

    :param page: the page number
    :type page: int
    :param limit: items per page
    :type limit: int
    :param order_by: the column to wich the order shall be perform
    :type order_by: string

    :returns: a list of intents
    :rtype: list
    '''

    try:
        check_access('user_intent_list', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system administrator'))

    kwargs = {}
    if data_dict.get('page'):
        kwargs['page'] = data_dict.get('page')
    if data_dict.get('limit'):
        kwargs['limit'] = data_dict.get('limit')
    if data_dict.get('order_by'):
        kwargs['order_by'] = data_dict.get('order_by')

    intents = UserIntents.get_list(**kwargs)
    items = []
    for i in intents:
        items.append(_table_dictize(i, context))

    return {
        'total': len(UserIntents.get_list()),
        'page': data_dict.get('page'),
        'size': data_dict.get('limit'),
        'items': items,
    }


@toolkit.side_effect_free
def user_intent_show(context, data_dict):
    ''' Shows a intent

    :param id: the intent ID
    :type id: string

    :returns: a intent
    :rtype: dictionary
    '''
    try:
        check_access('user_intent_show', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system administrator'))

    id = logic.get_or_bust(data_dict, 'id')

    intent = UserIntents.get(id)
    if not intent:
        raise NotFound(_(u'Intent'))

    return intent.as_dict()


@toolkit.side_effect_free
def user_query_show(context, data_dict):
    ''' Shows a user query

    :param id: the query ID
    :type id: string
    :param query_text: the user search query
    :type query_text: string
    :param query_type: the type of the search query
    :type query_type: string
    :param user_id: the ID of the user
    :type user_id: string

    :returns: a user query
    :rtype: dictionary
    '''

    kwargs = {}
    if data_dict.get('id'):
        kwargs['id'] = data_dict.get('id')
    if data_dict.get('query_text'):
        kwargs['query_text'] = data_dict.get('query_text')
    if data_dict.get('query_type'):
        kwargs['query_type'] = data_dict.get('query_type')
    if data_dict.get('user_id'):
        kwargs['user_id'] = data_dict.get('user_id')

    query = UserQuery.get(**kwargs)
    if not query:
        raise NotFound(_(u'User Query'))

    return query.as_dict()


@toolkit.side_effect_free
def user_query_list(context, data_dict):
    ''' List the user queries

    :param page: the page number
    :type page: int
    :param limit: items per page
    :type limit: int
    :param order_by: the column to wich the order shall be perform
    :type order_by: string

    :returns: a list of user queries
    :rtype: list
    '''
    try:
        check_access('user_query_list', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system administrator'))

    kwargs = {}
    if data_dict.get('page'):
        kwargs['page'] = data_dict.get('page')
    if data_dict.get('limit'):
        kwargs['limit'] = data_dict.get('limit')
    if data_dict.get('order_by'):
        kwargs['order_by'] = data_dict.get('order_by')

    queries = UserQuery.get_all(**kwargs)
    items = []
    for q in queries:
        items.append(_table_dictize(q, context))

    return {
        'total': len(UserQuery.get_all()),
        'page': data_dict.get('page'),
        'size': data_dict.get('limit'),
        'items': items,
    }


@toolkit.side_effect_free
def user_query_result_show(context, data_dict):
    ''' Shows a user query result

    :param id: the query result ID
    :type id: string

    :returns: a user query result
    :rtype: dictionary
    '''
    try:
        check_access('user_query_result_show', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system administrator'))

    id = logic.get_or_bust(data_dict, 'id')

    result = UserQueryResult.get(id)
    if not result:
        raise NotFound(_(u'User Query Result'))

    return result.as_dict()


@toolkit.side_effect_free
def user_query_result_search(context, data_dict):
    ''' Search the user query results

    :param q: the search query
    :type q: string
    :param page: the page number
    :type page: int
    :param limit: items per page
    :type limit: int
    :param order_by: the column to wich the order shall be perform
    :type order_by: string

    :returns: a list of user query results
    :rtype: list
    '''
    try:
        check_access('user_query_result_search', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system administrator'))

    kwargs = {}
    if data_dict.get('q'):
        kwargs['q'] = data_dict.get('q')
    if data_dict.get('page'):
        kwargs['page'] = data_dict.get('page')
    if data_dict.get('limit'):
        kwargs['limit'] = data_dict.get('limit')
    if data_dict.get('order_by'):
        kwargs['order_by'] = data_dict.get('order_by')

    results = UserQueryResult.search(**kwargs)
    items = []
    for r in results:
        items.append(_table_dictize(r, context))

    return {
        'total': len(UserQueryResult.search(**kwargs)),
        'page': data_dict.get('page'),
        'size': data_dict.get('limit'),
        'items': items,
    }


def _metrics_to_data_dict(metrics):
    result = {}
    for metric in ['completeness', 'uniqueness', 'timeliness', 'accuracy',
                   'validity', 'consistency']:
        result[metric] = getattr(metrics, metric) if metrics else None
    result['details'] = metrics.metrics
    return result


@toolkit.side_effect_free
def package_data_quality(context, data_dict):
    if not data_dict.get('id'):
        raise ValidationError({'id': _(u'Missing Value')})

    try:
        check_access('package_show', context, data_dict)
    except NotAuthorized as e:
        raise NotAuthorized(_(str(e)))

    metrics = DataQualityMetrics.get_dataset_metrics(data_dict['id'])
    if not metrics:
        raise NotFound(_('Not Found'))

    result = _metrics_to_data_dict(metrics)
    result['package_id'] = data_dict['id']
    calculated_on = metrics.modified_at or metrics.created_at
    if calculated_on:
        calculated_on = calculated_on.isoformat()
    result['calculated_on'] = calculated_on
    return result


@toolkit.side_effect_free
def resource_data_quality(context, data_dict):
    if not data_dict.get('id'):
        raise ValidationError({'id': _(u'Missing Value')})

    try:
        check_access('resource_show', context, data_dict)
    except NotAuthorized as e:
        raise NotAuthorized(_(str(e)))

    metrics = DataQualityMetrics.get_resource_metrics(data_dict['id'])
    if not metrics:
        raise NotFound(_('Not Found'))

    result = _metrics_to_data_dict(metrics)
    result['resource_id'] = data_dict['id']
    calculated_on = metrics.modified_at or metrics.created_at
    if calculated_on:
        calculated_on = calculated_on.isoformat()
    result['calculated_on'] = calculated_on

    return result


@toolkit.side_effect_free
def resource_validate_status(context, data_dict):

    if not data_dict.get('id'):
        raise ValidationError({'resource': _(u'Missing Value')})
    resource_id = data_dict.get('id')

    try:
        check_access('resource_validate_show', context, data_dict)
    except NotAuthorized as e:
        raise NotAuthorized(_(str(e)))

    filter = {"resource": resource_id}
    validation_status = ResourceValidate.get(**filter)
    if not validation_status:
        raise NotFound(_('Not Found'))

    return validation_status.as_dict()


def _tag_search(context, data_dict):
    model = context['model']

    terms = data_dict.get('query') or data_dict.get('q') or []
    if isinstance(terms, string_types):
        terms = [terms]
    terms = [t.strip() for t in terms if t.strip()]

    if 'fields' in data_dict:
        log.warning('"fields" parameter is deprecated.  '
                    'Use the "query" parameter instead')

    fields = data_dict.get('fields', {})
    offset = data_dict.get('offset')
    limit = data_dict.get('limit')

    # TODO: should we check for user authentication first?
    q = model.Session.query(model.Tag)

    if 'vocabulary_id' in data_dict:
        # Filter by vocabulary.
        vocab = model.Vocabulary.get(_get_or_bust(data_dict, 'vocabulary_id'))
        if not vocab:
            raise NotFound
        q = q.filter(model.Tag.vocabulary_id == vocab.id)

    for field, value in fields.items():
        if field in ('tag', 'tags'):
            terms.append(value)

    if not len(terms):
        return [], 0

    for term in terms:
        escaped_term = misc.escape_sql_like_special_characters(
            term, escape='\\')
        q = q.filter(model.Tag.name.ilike('%' + escaped_term + '%'))

    count = q.count()
    q = q.offset(offset)
    q = q.limit(limit)
    return q.all(), count


def tag_list(context, data_dict):
    '''Return a list of the site's tags.

    By default only free tags (tags that don't belong to a vocabulary) are
    returned. If the ``vocabulary_id`` argument is given then only tags
    belonging to that vocabulary will be returned instead.

    :param query: a tag name query to search for, if given only tags whose
        names contain this string will be returned (optional)
    :type query: string
    :param vocabulary_id: the id or name of a vocabulary, if give only tags
        that belong to this vocabulary will be returned (optional)
    :type vocabulary_id: string
    :param all_fields: return full tag dictionaries instead of just names
        (optional, default: ``False``)
    :type all_fields: bool

    :rtype: list of dictionaries

    '''
    from ckanext.knowledgehub.model.keyword import ExtendedTag

    model = context['model']

    id_of_tag = data_dict.get('id')
    vocab_id_or_name = data_dict.get('vocabulary_id')
    query = data_dict.get('query') or data_dict.get('q')
    if query:
        query = query.strip()
    all_fields = data_dict.get('all_fields', None)

    check_access('tag_list', context, data_dict)

    if query:
        tags, count = _tag_search(context, data_dict)
    elif vocab_id_or_name:
        tags = model.Tag.all(vocab_id_or_name)
    elif id_of_tag:
        filter = {"id": id_of_tag}
        tags = Session.query(model.Tag).filter(model.Tag.id == id_of_tag)
    else:
        tags = ExtendedTag.get_all()

    if tags:
        if all_fields:
            tag_list = [_table_dictize(tag, context) for tag in tags]
        else:
            tag_list = [tag.name for tag in tags]
    else:
        tag_list = []

    return tag_list


def tag_autocomplete(context, data_dict):
    '''Return a list of tag names that contain a given string.

    By default only free tags (tags that don't belong to any vocabulary) are
    searched. If the ``vocabulary_id`` argument is given then only tags
    belonging to that vocabulary will be searched instead.

    :param query: the string to search for
    :type query: string
    :param vocabulary_id: the id or name of the tag vocabulary to search in
      (optional)
    :type vocabulary_id: string
    :param fields: deprecated
    :type fields: dictionary
    :param limit: the maximum number of tags to return
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start returning tags
        from
    :type offset: int

    :rtype: list of strings

    '''
    check_access('tag_list', context, data_dict)
    matching_tags, count = _tag_search(context, data_dict)
    if matching_tags:
        return [tag.name for tag in matching_tags]
    else:
        return []


def tag_search(context, data_dict):
    '''Return a list of tags whose names contain a given string.

    By default only free tags (tags that don't belong to any vocabulary) are
    searched. If the ``vocabulary_id`` argument is given then only tags
    belonging to that vocabulary will be searched instead.

    :param query: the string(s) to search for
    :type query: string or list of strings
    :param vocabulary_id: the id or name of the tag vocabulary to search in
      (optional)
    :type vocabulary_id: string
    :param fields: deprecated
    :type fields: dictionary
    :param limit: the maximum number of tags to return
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start returning tags
        from
    :type offset: int

    :returns: A dictionary with the following keys:

      ``'count'``
        The number of tags in the result.

      ``'results'``
        The list of tags whose names contain the given string, a list of
        dictionaries.

    :rtype: dictionary

    '''
    tags, count = _tag_search(context, data_dict)
    if tags:
        for tag in tags:
            tag.__class__ = ExtendedTag
    return {'count': count,
            'results': [_table_dictize(tag, context) for tag in tags]}


def keyword_show(context, data_dict):
    '''Find a keyword by its name or id.

    :param id: `str`, the id or the name of the keyword to show.

    :returns: `dict`, the keyword data.
    '''
    check_access('keyword_show', context)
    if 'id' not in data_dict:
        raise ValidationError({
            'id': _('Missing Value')
        })
    keyword = Keyword.get(data_dict['id'])
    if not keyword:
        keyword = Keyword.by_name(data_dict['id'])

    if not keyword:
        raise logic.NotFound(_('No such keyword'))

    keyword_dict = _table_dictize(keyword, context)
    keyword_dict['tags'] = []
    for tag in Keyword.get_tags(keyword.id):
        keyword_dict['tags'].append(_table_dictize(tag, context))

    return keyword_dict


@toolkit.side_effect_free
def keyword_list(context, data_dict):
    '''Returns all keywords defined for this system.
    '''
    check_access('keyword_list', context)

    page = data_dict.get('page')
    limit = data_dict.get('limit')
    search = data_dict.get('q')

    results = []

    for keyword in Keyword.get_list(page, limit, search=search):
        results.append(toolkit.get_action('keyword_show')(context, {
            'id': keyword.id,
        }))

    return results


def rqs_search_tag(context, data_dict):
    '''
    Returns list of ids of research questions that have specific tag
    :param tags: `str`, the name of the tag.
    :returns: `list`, list of ids of research questions
    that have the specific tag.
    '''
    tag = data_dict.get('tags')
    result = []
    x = toolkit.get_action('research_question_list')(context, {})
    rq_list = toolkit.get_action('research_question_list')(
        context, {}
        ).get('data')

    for rq in rq_list:
        tags = rq.get('tags')
        if tags:
            for element in tags.split(','):
                if element == tag:
                    rq_id = rq.get('id')
                    result.append(rq_id)
    return result


def dash_search_tag(context, data_dict):
    '''
    Returns list of ids of dashboards that have specific tag.
    :param tags: `str`, the name of the tag.
    :returns: `list`, list of ids of dashboards that have the specific tag.
    '''
    tag = data_dict.get('tags')
    result = []
    x = toolkit.get_action('dashboard_list')(context, {})
    dash_list = x.get('data')

    for dash in dash_list:
        tags = dash.get('tags')
        if tags:
            for element in tags.split(','):
                if element == tag:
                    dash_id = dash.get('id')
                    result.append(dash_id)
    return result


def visual_search_tag(context, data_dict):
    '''
    Returns list of ids of visualizations that have specific tag.
    :param tags: `str`, the name of the tag.
    :returns: `list`, list of ids of visualizations that have the specific tag.
    '''
    tag = data_dict.get('tags')
    result = []
    visual_list = toolkit.get_action('resource_view_all')(context, {})

    for visual in visual_list:
        tags = visual.get('tags')
        if tags:
            for element in tags.split(','):
                if element == tag:
                    visual_id = visual.get('id')
                    result.append(visual_id)
    return result


def dataset_search_tag(context, data_dict):
    '''
    Returns list of ids of datasets that have specific tag.

    :param tags: `str`, the name of the tag.

    :returns: `list`, list of ids of datasets that have the specific tag.
    '''
    tag = data_dict.get('tags')
    result = []
    q = model.Session.query(model.package_tag_table).all()
    tag_id = model.Tag.by_name(name=tag).id
    dataset_tag_list = []

    for item in q:
        element = {
            "id": item[0],
            "package_id": item[1],
            "tag_id": item[2],
            "state": item[3],
            "revision_id": item[4]
        }
        dataset_tag_list.append(element)

    for dataset in dataset_tag_list:
        tags_id = dataset.get('tag_id')
        if tags_id == tag_id:
            result.append(dataset.get('package_id'))

    return result


def group_tags(context, data_dict):
    '''
    Group wrongly written tags and replace them with the correct tag.

    :param wrong_tags: `list` of `str`, the wrong tags to be grouped.
    :param new_tag: `str`, the correct tag.

    :returns: `dict`, the correct tag details.

    '''
    model = context['model']
    check_access('group_tags', context, data_dict)
    wrong_tags = data_dict.get('wrong_tags')
    new_tag = data_dict.get('new_tag')

    q = model.Session.query(model.tag_table).all()
    q_list = []
    for item in q:
        q_list.append(item.name)

    # Create new tag
    if new_tag not in q_list:
        correct_tag = toolkit.get_action('tag_create')(context, {
            'name': new_tag,
        })
    else:
        tag = model.Session.query(model.Tag).filter_by(
            name=new_tag
            ).first()
        extended_tag = ExtendedTag.get(
            tag.id,
            vocab_id_or_name=tag.vocabulary_id
            )
        extended_tag.__class__ = ExtendedTag
        correct_tag = model_dictize.tag_dictize(extended_tag, context)

    # Update tags in research questions, dashboards and visualizations
    for tag in wrong_tags:

        if tag not in q_list:
            log.debug('No such tag: %s', str(tag))
            raise logic.NotFound(_('Tag not found'))

        rq_list = toolkit.get_action('rqs_search_tag')(context, {
            'tags': tag
        })
        list_dashboard = toolkit.get_action('dash_search_tag')(context, {
            'tags': tag
        })
        list_visuals = toolkit.get_action('visual_search_tag')(context, {
            'tags': tag
        })
        list_datasets = toolkit.get_action('dataset_search_tag')(context, {
            'tags': tag
        })

        if len(rq_list):
            for rq in rq_list:
                toolkit.get_action('update_tag_in_rq')(context, {
                    'id': rq,
                    'tag_new': new_tag,
                    'tag_old': tag
                })
        if len(list_dashboard):
            for dash in list_dashboard:
                toolkit.get_action('update_tag_in_dash')(context, {
                    'id': dash,
                    'tag_new': new_tag,
                    'tag_old': tag
                })
        if len(list_visuals):
            for visual in list_visuals:
                toolkit.get_action('update_tag_in_resource_view')(context, {
                    'id': visual,
                    'new_tag': new_tag,
                    'old_tag': tag
                })
        if len(list_datasets):
            for single_dataset in list_datasets:
                toolkit.get_action('update_tag_in_dataset')(context, {
                    'id': single_dataset,
                    'new_tag': new_tag,
                    'old_tag': tag
                })

        # Delete the wrong tag from tag table
        toolkit.get_action('tag_delete_by_name')(context, {
            'name': tag
        })

    return correct_tag


def _show_user_profile(context, user_id):
    profile = UserProfile.by_user_id(user_id)
    if not profile:
        raise logic.NotFound(_('No such user profile'))

    interests = {
        'research_questions': [],
        'keywords': [],
        'tags': [],
    }
    for interest, show_action in {
        'research_questions': 'research_question_show',
        'keywords': 'keyword_show',
        'tags': 'tag_show',
    }.items():
        for value in (profile.interests or {}).get(interest, []):
            try:
                entity = toolkit.get_action(show_action)(context, {
                    'id': value,
                })
                interests[interest].append(entity)
            except logic.NotFound:
                log.debug('Not found "%s" with id %s', interest, value)

    profile_dict = _table_dictize(profile, context)
    profile_dict['interests'] = interests
    return profile_dict


@toolkit.side_effect_free
def user_profile_show(context, data_dict):
    u'''Returns the data for the user profile for the currently authenticated
    user.

    If the user is a sysadmin, it can provide a specific user_id to get the
    user profile for a particular user besides his own user account.

    :param user_id: `str`, the ID of the user to display the user profile. The
        parameter is available only if the current user is a sysadmin,
        otherwise this parameter is ignored.
    '''
    check_access('user_profile_show', context)

    user = context.get('auth_user_obj')
    if getattr(user, 'sysadmin', False):
        if data_dict.get('user_id'):
            return _show_user_profile(context, data_dict['user_id'])

    return _show_user_profile(context, user.id)


def user_profile_list(context, data_dict):
    u'''Returns a list of all user profiles.

    Available only for sysadmin users.
    '''
    check_access('user_profile_list', context)
    page = data_dict.get('page', 1)
    limit = data_dict.get('limit', 20)

    order_by = data_dict.get('order')

    profiles = UserProfile.get_list(page, limit, order_by)

    results = []

    for profile in profiles:
        results.append(_table_dictize(profile, context))

    return results


@toolkit.side_effect_free
def tag_list_search(context, data_dict):
    u'''Performs a search for tags, similar to tag_search, however it returns
    the full data for the found tags.
    '''
    context['ignore_auth'] = True
    results = toolkit.get_action('tag_list')(context, data_dict)
    tags = []
    for tag_name in results:
        tags.append(
            toolkit.get_action('tag_show')(context, {'id': tag_name})
        )
    context.pop('ignore_auth')
    return tags


@toolkit.side_effect_free
def tag_show(context, data_dict):
    '''Return the details of a tag and all its datasets.

    :param id: the name or id of the tag
    :type id: string
    :param vocabulary_id: the id or name of the tag vocabulary that the tag is
        in - if it is not specified it will assume it is a free tag.
        (optional)
    :type vocabulary_id: string
    :param include_datasets: include a list of the tag's datasets. (Up to a
        limit of 1000 - for more flexibility, use package_search - see
        :py:func:`package_search` for an example.)
        (optional, default: ``False``)
    :type include_datasets: bool

    :returns: the details of the tag, including a list of all of the tag's
        datasets and their details
    :rtype: dictionary
    '''

    model = context['model']
    id = _get_or_bust(data_dict, 'id')
    include_datasets = asbool(data_dict.get('include_datasets', False))

    tag = ExtendedTag.get(id, vocab_id_or_name=data_dict.get('vocabulary_id'))
    context['tag'] = tag

    if tag is None:
        raise NotFound

    tag = ExtendedTag.get_with_keyword(tag.id)
    context['tag'] = tag
    tag.__class__ = ExtendedTag

    check_access('tag_show', context, data_dict)
    return model_dictize.tag_dictize(tag, context,
                                     include_datasets=include_datasets)


def package_search(context, data_dict=None):
    '''Overrides CKAN's package_search action to add boost parameters for the
    user interests.
    '''
    user = context.get('auth_user_obj')
    if user:
        data_dict = data_dict or {}
        data_dict['boost_for'] = user.id
    return ckan_package_search(context, data_dict)


def notification_list(context, data_dict):
    '''Lists the unread notifications for the current user.

    :param user_id: `str`, the id of the recepient of the notifications. Only
        available for sysadmin users.
    :param limit: `int`, how many notifications to show (max).
    :param offset: `int`, how many notifications to skip (pagination).

    :returns: `dict`, the notifications list and count. The count is available
    as `count` and the list of notifications is available under `results`.
    '''
    check_access('notification_list', context)

    limit = data_dict.get('limit')
    offset = data_dict.get('offset')

    user = context['auth_user_obj']

    user_id = data_dict.get('user_id')

    if not (
            (hasattr(user, 'sysadmin') and user.sysadmin) or
            context.get('ignore_auth')):
        user_id = user.id
    if not user_id:
        user_id = user.id

    count = Notification.get_notifications_count(user_id)
    notifications = []
    if count:
        notifications = Notification.get_notifications(user_id, limit, offset)

    result = {
        'count': count,
        'results': [],
    }

    for notification in notifications:
        notification = _table_dictize(notification, context)
        for field in ['link', 'image']:
            if notification.get(field):
                notification[field] = notification[field].encode('ascii')
        result['results'].append(notification)

    return result


@toolkit.side_effect_free
def notification_show(context, data_dict):
    '''Display the data for a particular notification.
    A user can only read notification to which it is set as a recepient.

    :param id: `str`, the notification id.

    :returns: `dict`, the data for the notification if found and available.
    '''
    check_access('notification_list', context)

    if 'id' not in data_dict:
        raise ValidationError({'id': _('Missing value')})

    user = context['auth_user_obj']

    notification = Notification.get(data_dict['id'])
    if not notification:
        raise logic.NotFound(_('Not found'))

    if notification.recepient != user.id:
        raise logic.NotAuthorized(_('Not authorized to see this notifiation.'))

    notification = _table_dictize(notification, context)
    for field in ['link', 'image']:
        if notification.get(field):
            notification[field] = notification[field].encode('ascii')
    return notification
