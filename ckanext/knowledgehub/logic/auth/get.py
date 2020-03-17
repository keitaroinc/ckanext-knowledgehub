import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
from ckan.logic.auth.get import (
    tag_list as ckan_tag_list,
    package_search as ckan_package_search,
)
from ckan.logic import chained_action



@toolkit.auth_allow_anonymous_access
def research_question_show(context, data_dict):
    return {'success': True}


@toolkit.auth_allow_anonymous_access
def research_question_list(context, data_dict):
    return {'success': True}


@toolkit.auth_allow_anonymous_access
def dashboard_list(context, data_dict):
    return {'success': True}


def dashboard_show(context, data_dict):
    search_query = {'text': '*'}
    if data_dict.get('id'):
        search_query['entity_id'] = data_dict.get('id')
    elif data_dict.get('name'):
        search_query['name'] = data_dict.get('name')
    else:
        return {'success': False}

    docs = toolkit.get_action('search_dashboards')(
        {'ignore_auth': True},
        search_query
    )
    if docs.get('count', 0) == 1:
        dashboard = docs['results'][0]
        datasets_str = dashboard.get('datasets', '')
        if datasets_str:
            datasets = datasets_str.split(', ')
            for dataset in datasets:
                try:
                    context.pop('package', None)
                    a = toolkit.check_access(
                        'package_show', context, {'id': dataset})
                except toolkit.NotAuthorized:
                    return {'success': False}

            return {'success': True}

    return {'success': False}


def intent_list(context, data_dict):
    # sysadmins only
    return {'success': False}


def user_intent_show(context, data_dict):
    # sysadmins only
    return {'success': False}


def user_query_show(context, data_dict):
    # sysadmins only
    return {'success': False}


def user_intent_list(context, data_dict):
    # sysadmins only
    return {'success': False}


def user_query_list(context, data_dict):
    # sysadmins only
    return {'success': False}


def user_query_result_show(context, data_dict):
    # sysadmins only
    return {'success': False}


def user_query_result_search(context, data_dict):
    # sysadmins only
    return {'success': False}


def resource_validate_show(context, data_dict):
    # all users
    return {'success': True}


def tag_list(context, data_dict):
    # sysadmins only
    return {'success': False}


def keyword_show(context, data_dict):
    '''
    Authorization check for fetching a keyword. Authorized users.
    '''
    # sysadmins only
    return {'success': True}


def tag_show(context, data_dict):
    '''
    Authorization check for fetching a keyword. Authorized users.
    '''
    # sysadmins only
    return {'success': True}


def keyword_list(context, data_dict):
    '''
        Authorization check for getting the list of keywords. Sysadmin only.
    '''
    return {'success': True}


def group_tags(context, data_dict):
    '''
        Authorization check for grouping sets of tags.
    '''
    return {'success': True}


def user_profile_show(context, data_dict):
    user = context.get('auth_user_obj')
    if not user:
        return {'success': False}
    if data_dict and data_dict.get('user_id'):
        if getattr(user, 'sysadmin', False):
            # Sysadmin can read all profiles
            return {'success': True}
        # Must be sysadmin to see all profiles
        return {'suceess': False}
    # User can view its own profile
    return {'success': True}


def user_profile_list(context, data_dict=None):
    return {'success': False}


def package_search(context, data_dict=None):
    return ckan_package_search(context, data_dict)


def push_data_to_hdx(context, data_dict):
    '''
        Authorization check for pushing data to hdx. Authorized users.
    '''
    return {'success': True}


def notification_list(context, data_dict=None):
    return {'success': True}


def notification_show(context, data_dict):
    return {'success': True}
