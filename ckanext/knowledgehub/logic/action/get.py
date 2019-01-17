import logging

import ckan.logic as logic
from ckan.plugins import toolkit
from ckan.common import _
from ckan import lib

from ckanext.knowledgehub.model import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion


log = logging.getLogger(__name__)

_table_dictize = lib.dictization.table_dictize
check_access = toolkit.check_access
NotFound = logic.NotFound
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

    :returns: a sub-theme
    :rtype: dictionary
    '''

    id = logic.get_or_bust(data_dict, 'id')
    st = SubThemes.get(id=id).first()

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
    return (optional, default: ``10``)
    :type pageSize: int

    :returns: a dictionary including total
    items, page number, page size and data(sub-themes)
    :rtype: dictionary
    '''

    page_size = int(data_dict.get('pageSize', 10))
    page = int(data_dict.get('page', 1))
    offset = (page - 1) * page_size
    st_list = []

    st_db_list = SubThemes.get(limit=page_size,
                               offset=offset,
                               order_by='name asc').all()

    for entry in st_db_list:
        st_list.append(_table_dictize(entry, context))

    total = len(SubThemes.get().all())

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
    id = data_dict.get('id')

    rq = ResearchQuestion.get(id=id).first()
    print rq
    if not rq:
        raise toolkit.ObjectNotFound
    return rq.as_dict()


@toolkit.side_effect_free
def research_question_list(context, data_dict):
    ''' List research questions

    :param page: current page in pagination (optional, default: ``1``)
    :type page: int
    :param pageSize: the number of items
    to return (optional, default: ``10``)
    :type pageSize: int

    :returns: a dictionary including total
     items, page number, page size and data
    :rtype: dictionary
    '''

    page_size = int(data_dict.get('pageSize', 10))
    page = int(data_dict.get('page', 1))
    offset = (page - 1) * page_size
    rq_list = []

    rq_db_list = ResearchQuestion.get(limit=page_size,
                                      offset=offset,
                                      order_by='name asc').all()

    for entry in rq_db_list:
        rq_list.append(_table_dictize(entry, context))

    total = len(ResearchQuestion.get().all())

    return {'total': total, 'page': page,
            'pageSize': page_size, 'data': rq_list}
