from ckan.common import _
import ckan.authz as authz
from ckan.logic import NotAuthorized


def analytical_framework_delete(context, data_dict):
    user = context.get('user')
    if not user:
        raise NotAuthorized(_('unauthenticated user'))

    if not authz.is_sysadmin(user):
        raise NotAuthorized(_('authenticated user must have KHA role'))

    return {'success': True}


def analytical_framework_list(context, data_dict):
    return {'success': True}
