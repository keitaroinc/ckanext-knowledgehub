import logging
import os
import json

import ckan.logic as logic
from ckan.plugins import toolkit
from ckan.common import _
from ckan import lib
from ckan import model

from ckanext.knowledgehub.model import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.model import Dashboard
from ckanext.knowledgehub.model import ResourceFeedbacks
from ckanext.knowledgehub.model import KWHData
from ckanext.knowledgehub.model import RNNCorpus
from ckanext.knowledgehub import helpers as kh_helpers
from ckanext.knowledgehub.rnn import helpers as rnn_helpers
from ckan.lib import helpers as h
from ckan.controllers.admin import get_sysadmins

from ckanext.knowledgehub.backend.factory import get_backend
from ckanext.knowledgehub.lib.writer import WriterService


log = logging.getLogger(__name__)

_table_dictize = lib.dictization.table_dictize
model_dictize = lib.dictization.model_dictize
check_access = toolkit.check_access
NotFound = logic.NotFound
_get_or_bust = logic.get_or_bust
ValidationError = toolkit.ValidationError


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
    # print stream.getvalue()

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

    dashboards = []

    t_db_list = Dashboard.search(q=q,
                                 limit=limit,
                                 offset=offset,
                                 order_by=sort)\
        .all()

    for dashboard in t_db_list:
        dashboards.append(_table_dictize(dashboard, context))

    total = len(Dashboard.search().all())

    return {u'total': total, u'page': page,
            u'items_per_page': limit, u'data': dashboards}


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

    sysadmin = get_sysadmins()[0].name
    context = {'user': sysadmin, 'ignore_auth': True}

    datasets = toolkit.get_action('package_search')(context, {
        'fq': '+extras_research_question:{0}'.format(research_question)
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
    page_size = int(data_dict.get('pageSize', 1000000))
    page = int(data_dict.get('page', 1))
    order_by = data_dict.get('order_by', None)
    offset = (page - 1) * page_size

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
    kwargs['limit'] = page_size
    kwargs['offset'] = offset
    kwargs['order_by'] = order_by

    kwh_data = []

    try:
        db_data = KWHData.get(**kwargs).all()
    except Exception:
        return {'total': 0, 'page': page,
                'pageSize': page_size, 'data': []}

    for entry in db_data:
        kwh_data.append(_table_dictize(entry, context))

    total = len(kwh_data)

    return {'total': total, 'page': page,
            'pageSize': page_size, 'data': kwh_data}


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


@toolkit.side_effect_free
def get_predictions(context, data_dict):
    ''' Returns a list of predictions
    :param text: the text for which predictions have to be made
    :type text: string
    :returns: predictions
    :rtype: list
    '''

    text = data_dict.get('text')
    if not text:
        raise ValidationError({'text': _('Missing value')})

    return rnn_helpers.predict_completions(text)
