from ckan.plugins import toolkit

not_empty = toolkit.get_validator('not_empty')
ignore_empty = toolkit.get_validator('ignore_empty')

def sub_theme_create():
    return {
        'name': [not_empty, unicode],
        'description': [ignore_empty, unicode],
        'theme_id': [not_empty, unicode]
    }