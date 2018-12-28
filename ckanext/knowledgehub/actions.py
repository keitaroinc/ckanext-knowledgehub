from ckan.common import _
from ckan.plugins import toolkit
from ckan.logic import (check_access,
                        NotAuthorized,
                        NotFound)
import ckan.lib.navl.dictization_functions

from ckanext.knowledgehub.model import AnalyticalFramework

from pprint import pprint as pprint

_table_dictize = ckan.lib.dictization.table_dictize


@toolkit.side_effect_free
def analytical_framework_delete(context, data_dict):
    try:
        check_access('analytical_framework_delete', context, data_dict)
    except:
        raise

    af_id = data_dict.get('id', '')
    try:
        AnalyticalFramework.delete(af_id)
    except:
        raise

    return 'OK'


@toolkit.side_effect_free
def analytical_framework_list(context, data_dict):
    limit = data_dict.get('limit')
    af_list = []
    if limit:
        af_db_list = AnalyticalFramework.get_all(limit=limit)
    else:
        af_db_list = AnalyticalFramework.get_all()

    for entry in af_db_list:
        af_list.append(_table_dictize(entry, context))
    return af_list
