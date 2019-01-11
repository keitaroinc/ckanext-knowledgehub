def theme_update(context, data_dict):
    '''
        Authorization check for updating theme
    '''
    # sysadmins only
    return {'success': False}
