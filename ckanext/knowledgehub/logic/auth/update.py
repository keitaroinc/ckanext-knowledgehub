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

from ckan.logic.auth.update import package_update as ckan_package_update
from ckan.logic.auth.update import resource_update as ckan_resource_update

from ckan.plugins import toolkit


def theme_update(context, data_dict):
    '''
        Authorization check for updating
        a theme
    '''
    # sysadmins only
    return {'success': False}


def sub_theme_update(context, data_dict):
    '''
        Authorization check for updating
        a sub theme
    '''
    # sysadmins only
    return {'success': False}


def research_question_update(context, data_dict):
    '''
        Authorization check for updating
        a research question
    '''
    # sysadmins only
    return {'success': False}


def dashboard_update(context, data_dict):
    '''
        Authorization check for updating
        a dashboard
    '''
    # sysadmins only
    return {'success': False}


def resource_validation_update(context, data_dict):
    '''
        Authorization check for updating
        a resource validation
    '''
    # sysadmins only
    return {'success': True}


def resource_validation_status(context, data_dict):
    '''
        Authorization check for updating
        a resource validation status
    '''
    # sysadmins only
    return {'success': True}


def resource_validation_revert(context, data_dict):
    '''
        Authorization check for updating
        a resource validation revert
    '''
    # sysadmins only
    return {'success': True}


def package_update(context, data_dict=None):
    # This auth function must be overriden like this, otherwise an error is
    # thrown in a dataset page for a regular user.
    return ckan_package_update(context, data_dict)


def resource_validate_update(context, data_dict):
    '''
        Authorization check for updating
        a validation status
    '''
    # all users
    return {'success': True}


def resource_update(context, data_dict=None):
    # This auth function must be overriden like this, otherwise an error is
    # thrown when a regular user is adding new resource.
    return ckan_resource_update(context, data_dict)


def keyword_update(context, data_dict=None):
    '''
        Authorization check for updating a keyword. Sysadmin only.
    '''
    return {'success': False}


def user_profile_update(context, data_dict):
    return {'success': True}


@toolkit.chained_auth_function
def datastore_create(action, context, data_dict=None):
    return {'success': True}


def notifications_read(context, data_dict):
    return {'success': True}


def access_request_grant(context, data_dict):
    return {'success': True}


def access_request_decline(context, data_dict):
    return {'success': True}


def comment_update(context, data_dict=None):
    return {'success': True}
