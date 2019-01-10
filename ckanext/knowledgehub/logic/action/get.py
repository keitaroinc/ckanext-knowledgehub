from ckan.plugins import toolkit
from ckan import lib
from ckan import logic
from ckan.common import _

from ckanext.knowledgehub.model import SubThemes


_table_dictize = lib.dictization.table_dictize


@toolkit.side_effect_free
def sub_theme_show(context, data_dict):
    id = logic.get_or_bust(data_dict, 'id')
    st = SubThemes.get(id=id).first()

    if not st:
        raise logic.NotFound(_(u'Sub-theme'))

    return st.as_dict()

@toolkit.side_effect_free
def sub_theme_list(context, data_dict):
    page_size = int(data_dict.get('pageSize', 10))
    page = int(data_dict.get('page', 1))
    offset = (page - 1) * page_size
    st_list = []

    st_db_list = SubThemes.get(limit=page_size, offset=offset, order_by='name asc').all()

    for entry in st_db_list:
        st_list.append(_table_dictize(entry, context))

    total = len(SubThemes.get().all())

    return {'total': total, 'page': page, 'pageSize': page_size, 'data': st_list}