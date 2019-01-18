from ckan.plugins import toolkit
from ckanext.knowledgehub.logic import validators

not_empty = toolkit.get_validator('not_empty')
ignore_missing = toolkit.get_validator('ignore_missing')
name_validator = toolkit.get_validator('name_validator')
isodate = toolkit.get_validator('isodate')
ignore_empty = toolkit.get_validator('ignore_empty')


def theme_schema():
    return {
        'name': [not_empty,
                 name_validator,
                 validators.theme_name_validator,
                 unicode],
        'title': [not_empty, unicode],
        'description': [ignore_missing, unicode],
        'created_at': [ignore_missing, isodate],
        'modified_at': [ignore_missing, isodate],
    }


def sub_theme_create():
    return {
        'title': [not_empty, unicode],
        'name': [not_empty,
                 name_validator,
                 validators.sub_theme_name_validator,
                 unicode],
        'description': [ignore_empty, unicode],
        'theme': [not_empty, unicode]
    }


def sub_theme_update():
    return {
        'title': [not_empty, unicode],
        'name': [not_empty,
                 name_validator,
                 validators.sub_theme_name_validator,
                 unicode],
        'description': [ignore_empty, unicode],
        'theme': [not_empty, unicode]
    }


def research_question_schema():
    return {
        'id': [ignore_missing, unicode],
        'theme': [not_empty, unicode],
        'sub_theme': [not_empty, unicode],
        'content': [not_empty, unicode],
    }
