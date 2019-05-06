
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
