def theme_delete(context, data_dict):
    '''
        Authorization check for creating theme
    '''
    # sysadmins only
    return {'success': False}
