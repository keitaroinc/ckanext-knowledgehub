from ckan.common import _

import ckan.authz as authz
import ckan.logic as logic


def analytical_framework_delete(context, data_dict):
    user = context.get('user')
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized

    return {'success': True}


def analytical_framework_list(context, data_dict):
    return {'success': True}
