"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

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

    # The search would take into consideration the type of authenticated user
    # in the context and will perform a search based on the pemrission labels.
    # If this document is not found, then the user does not have a permission
    # to access this dashboard.
    docs = toolkit.get_action('search_dashboards')(
        context,
        search_query
    )

    if docs.get('count') > 0:
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


def get_groups_for_user(context, data_dict=None):
    return {'success': False}


def post_show(context, data_dict=None):
    return {'success': True}


def post_search(context, data_dict=None):
    return {'success': True}


def access_request_list(context, data_dict=None):
    return {'success': True}


def comments_list(context, data_dict=None):
    return {'success': True}


def comments_thread_show(context, data_dict=None):
    return {'success': True}


def resolve_mentions(context, data_dict=None):
    return {'success': False}


def get_liked_by_user(context, data_dict=None):
    return {'success': True}


def get_request_log(context, data_dict=None):
    return {'success': False}


def get_request_log_report(context, data_dict=None):
    return {'success': False}
