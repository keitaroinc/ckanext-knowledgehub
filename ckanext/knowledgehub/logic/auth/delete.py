
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
