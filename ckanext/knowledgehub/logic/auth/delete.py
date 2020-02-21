from ckan.logic.auth.delete import package_delete as ckan_package_delete


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
    # sysadmins only
    return {'success': False}


def keyword_delete(context, data_dict=None):
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
