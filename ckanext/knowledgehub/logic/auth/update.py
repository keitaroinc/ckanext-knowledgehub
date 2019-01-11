import ckan.authz as authz
import ckan.logic as logic


def theme_update(context, data_dict):
    '''
        Authorization check for updating theme
    '''
    # sysadmins only
    return {'success': False}


def sub_theme_update(context, data_dict):
    user = context.get('user')
    if not authz.is_sysadmin(user):
        raise logic.NotAuthorized

    return {'success': True}


def research_question_update(context, data_dict):
    user = context.get('user')
    author = data_dict.get('author')
    if user == author or authz.is_sysadmin(user):
        return {'success': True}
    else:
        return {'success': False}
