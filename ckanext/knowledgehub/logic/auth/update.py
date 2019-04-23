
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
