from ckan.common import _
from ckan.plugins import toolkit
from ckan.logic import (check_access,
                        NotAuthorized,
                        NotFound)

from ckanext.knowledgehub.model import AnalyticalFramework


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
    check_access('analytical_framework_list', context, data_dict)

    limit = data_dict.get('limit', None)

    if limit:
        return AnalyticalFramework.get_all(limit=limit)
    else:
        return AnalyticalFramework.get_all()
