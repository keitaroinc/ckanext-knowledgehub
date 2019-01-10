import ckan.authz as authz


def sub_theme_update(context, data_dict):
    user = context.get('user')
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized

    return {'success': True}