import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
from ckan.logic.auth.get import tag_list as ckan_tag_list


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


def tag_list(context, data_dict):
    # sysadmins only
    return {'success': False}
