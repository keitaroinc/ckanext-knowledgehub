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

from ckan.logic.auth.delete import package_delete as ckan_package_delete
from ckan.logic.auth.delete import resource_delete as ckan_resource_delete


def theme_delete(context, data_dict):
    '''
        Authorization check for deleting
        a theme
    '''
    # sysadmins only
    return {'success': False}


def sub_theme_delete(context, data_dict):
    '''
        Authorization check for deleting
        a sub theme
    '''
    # sysadmins only
    return {'success': False}


def research_question_delete(context, data_dict):
    '''
        Authorization check for deleting
        a research question
    '''
    # sysadmins only
    return {'success': False}


def dashboard_delete(context, data_dict):
    '''
        Authorization check for deleting a dashboard
    '''
    # sysadmins only
    return {'success': False}


def user_intent_delete(context, data_dict):
    '''
        Authorization check for deleting a user intent
    '''
    # sysadmins only
    return {'success': False}


def resource_validate_delete(context, data_dict):
    '''
        Authorization check for deleting a validation status of resource
    '''
    # all users
    return {'success': True}


def keyword_delete(context, data_dict=None):
    '''
        Authorization check for deletion of a keyword. Sysadmin only.
    '''
    return {'success': False}


def tag_delete_by_name(context, data_dict=None):
    '''
        Authorization check for deletion of a keyword. Sysadmin only.
    '''
    return {'success': False}


def package_delete(context, data_dict):
    '''
    This auth function must be overriden like this,
    otherwise a recursion error is thrown.
    '''
    return ckan_package_delete(context, data_dict)


def post_delete(context, data_dict=None):
    return {'success': True}


def comment_delete(context, data_dict=None):
    return {'success': True}


def like_delete(context, data_dict=None):
    return {'success': True}

def resource_delete(context, data_dict):
    return {'success': True }

