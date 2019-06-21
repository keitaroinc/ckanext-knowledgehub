from ckan.logic.auth.create import package_create as ckan_package_create


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


def package_create(context, data_dict=None):
    # This auth function must be overriden like this, otherwise a recursion
    # error is thrown when the /dataset page is accessed by a regular user
    return ckan_package_create(context, data_dict)


def kwh_data(context, data_dict):
    '''
        Authorization check for storing KWH data
    '''
    # sysadmins only
    return {'success': False}


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
