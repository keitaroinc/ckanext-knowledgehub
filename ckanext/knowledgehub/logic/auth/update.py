from ckan.logic.auth.update import package_update as ckan_package_update
from ckan.logic.auth.update import resource_update as ckan_resource_update


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


def package_update(context, data_dict=None):
    # This auth function must be overriden like this, otherwise an error is
    # thrown in a dataset page for a regular user.
    return ckan_package_update(context, data_dict)


def resource_validate_update(context, data_dict):
    '''
        Authorization check for updating
        a validation status
    '''
    # sysadmins only
    return {'success': False}


def resource_update(context, data_dict=None):
    # This auth function must be overriden like this, otherwise an error is
    # thrown when a regular user is adding new resource.
    return ckan_resource_update(context, data_dict)
