import logging

import ckan.logic as logic
from ckan.plugins import toolkit
from ckan.common import _
from ckan import lib

from ckanext.knowledgehub.model import Theme
from ckanext.knowledgehub.model import SubThemes


log = logging.getLogger(__name__)

_table_dictize = lib.dictization.table_dictize
check_access = logic.check_access
NotFound = logic.NotFound
ValidationError = logic.ValidationError


@toolkit.side_effect_free
def theme_show(context, data_dict):
    '''
        Returns existing analytical framework Theme

    :param id
    '''

    check_access('theme_update', context)

    if 'id' not in data_dict:
        raise ValidationError({"id": "Missing parameter"})

    theme = Theme.get(id=data_dict['id']).first()

    if not theme:
        log.debug('Could not find theme %s', id)
        raise NotFound(_(u'Theme was not found.'))

    return _table_dictize(theme, context)


@toolkit.side_effect_free
def theme_list(context, data_dict):
    ''' List themes

    :param page: current page in pagination (optional, default: ``1``)
    :type page: int
    :param pageSize: the number of items to return (optional, default: ``10``)
    :type pageSize: int

    :returns: a dictionary including total items,
     page number, page size and data(themes)
    :rtype: dictionary
    '''

    page_size = int(data_dict.get('pageSize', 10))
    page = int(data_dict.get('page', 1))
    offset = (page - 1) * page_size
    themes = []

    t_db_list = Theme.get(limit=page_size,
                          offset=offset,
                          order_by='name asc').all()

    for entry in t_db_list:
        themes.append(_table_dictize(entry, context))

    total = len(Theme.get().all())

    return {'total': total, 'page': page,
            'pageSize': page_size, 'data': themes}


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
