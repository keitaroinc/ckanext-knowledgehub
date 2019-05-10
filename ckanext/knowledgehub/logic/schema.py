from ckan.plugins import toolkit
from ckanext.knowledgehub.logic import validators

not_empty = toolkit.get_validator('not_empty')
ignore_missing = toolkit.get_validator('ignore_missing')
name_validator = toolkit.get_validator('name_validator')
isodate = toolkit.get_validator('isodate')
ignore_empty = toolkit.get_validator('ignore_empty')
email_validator = toolkit.get_validator('email_validator')
convert_to_json_if_string = toolkit.get_converter('convert_to_json_if_string')
package_id_or_name_exists = toolkit.get_converter('package_id_or_name_exists')
resource_id_exists = toolkit.get_converter('resource_id_exists')


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
        'theme': [ignore_missing, unicode],
        'sub_theme': [ignore_missing,
                      validators.check_sub_theme_parent,
                      unicode],
        'title': [not_empty,
                  validators.research_question_title_validator,
                  validators.research_question_title_characters_validator,
                  unicode],
        'image_url': [ignore_missing, unicode]
    }


def resource_view_schema():
    return {
        'resource_id': [not_empty],
        'title': [not_empty, unicode],
        'description': [ignore_missing, unicode],
        'view_type': [not_empty, unicode]
    }


def dashboard_schema():
    return {
        'name': [not_empty,
                 name_validator,
                 validators.dashboard_name_validator,
                 unicode],
        'title': [not_empty, unicode],
        'description': [not_empty, unicode],
        'type': [not_empty,
                 validators.dashboard_type_validator,
                 unicode],
        'created_at': [ignore_missing, isodate],
        'modified_at': [ignore_missing, isodate],
        'source': [ignore_missing,
                   validators.dashboard_source_validator,
                   unicode],
        'indicators': [ignore_missing,
                       convert_to_json_if_string,
                       unicode],
    }


def resource_feedback_schema():
    return {
        'type': [not_empty, validators.resource_feedbacks_type_validator],
        'dataset': [not_empty, package_id_or_name_exists],
        'resource': [not_empty, resource_id_exists]
    }
