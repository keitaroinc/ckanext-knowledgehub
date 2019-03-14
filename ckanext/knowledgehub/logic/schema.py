from ckan.plugins import toolkit
from ckanext.knowledgehub.logic import validators

not_empty = toolkit.get_validator('not_empty')
ignore_missing = toolkit.get_validator('ignore_missing')
name_validator = toolkit.get_validator('name_validator')
isodate = toolkit.get_validator('isodate')
ignore_empty = toolkit.get_validator('ignore_empty')
email_validator = toolkit.get_validator('email_validator')


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
        'author': [ignore_missing],
        'author_email': [ignore_missing,
                         email_validator],
        'state': [ignore_missing]
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
        'name': [not_empty,
                 name_validator,
                 validators.research_question_name_validator,
                 unicode],
        'theme': [not_empty, unicode],
        'sub_theme': [not_empty,
                      validators.check_sub_theme_parent,
                      unicode],
        'title': [not_empty, unicode],
    }


def resource_view_schema():
    return {
        'resource_id': [not_empty],
        'title': [not_empty, unicode],
        'description': [ignore_missing, unicode],
        'view_type': [not_empty, unicode],
        'config': [not_empty],
    }
