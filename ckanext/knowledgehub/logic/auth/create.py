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

from ckan.logic.auth.create import (
    package_create as ckan_package_create,
    resource_create as ckan_resource_create,
    member_create as ckan_member_create,
)


def theme_create(context, data_dict):
    '''
        Authorization check for creating
        a theme
    '''
    # sysadmins only
    return {'success': False}


def sub_theme_create(context, data_dict):
    '''
        Authorization check for creating
        a sub theme
    '''
    # sysadmins only
    return {'success': False}


def research_question_create(context, data_dict):
    '''
        Authorization check for creating
        a research question
    '''
    # sysadmins only
    return {'success': False}


def dashboard_create(context, data_dict):
    '''
        Authorization check for creating dashboard
    '''
    # sysadmins only
    return {'success': False}


def resource_feedback(context, data_dict):
    '''
        Authorization check for resource feedback
    '''
    # all users
    return {'success': True}


def resource_validation_create(context, data_dict):
    '''
        Authorization check for resource validation
    '''
    # all users
    return {'success': True}


def package_create(context, data_dict=None):
    # This auth function must be overriden like this, otherwise a recursion
    # error is thrown when the /dataset page is accessed by a regular user
    return ckan_package_create(context, data_dict)


def resource_create(context, data_dict=None):
    # This auth function must be overriden like this, otherwise a recursion
    # error is thrown when the /new_resource page is accessed by a regular user
    return ckan_resource_create(context, data_dict)


def kwh_data(context, data_dict):
    '''
        Authorization check for storing KWH data
    '''
    # all login users
    return {'success': True}


def corpus_create(context, data_dict):
    '''
        Authorization check for storing RNN corpus
    '''
    # sysadmins only
    return {'success': False}


def run_command(context, data_dict):
    '''
        Authorization check for running commands
    '''
    # sysadmins only
    return {'success': False}


def user_intent_create(context, data_dict):
    '''
        Authorization check for user intent create
    '''
    # sysadmins only
    return {'success': False}


def user_query_create(context, data_dict):
    '''
        Authorization check for user query create
    '''
    # sysadmins only
    return {'success': False}


def user_query_result_create(context, data_dict):
    '''
        Authorization check for user query result create
    '''
    # sysadmins only
    return {'success': False}


def resource_validate_create(context, data_dict):
    '''
        Authorization check for validation status of resource
    '''
    # all users
    return {'success': True}


def keyword_create(context, data_dict):
    '''
        Authorization check for creation of a keyword. Sysadmin only.
    '''
    # sysadmins only
    return {'success': False}


def user_profile_create(context, data_dict=None):
    return {'success': True}


def notification_create(context, data_dict=None):
    return {'success': True}


def member_create(context, data_dict=None):
    return ckan_member_create(context, data_dict)


def post_create(context, data_dict=None):
    return {'success': True}


def request_access(context, data_dict=None):
    return {'success': True}


def comment_create(context, data_dict=None):
    return {'success': True}


def notify_tagged(context, data_dict):
    return {'success': false}

def like_create(context, data_dict=None):
    return {'success': True}
