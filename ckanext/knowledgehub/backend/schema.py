from ckan.plugins import toolkit
from ckanext.knowledgehub.logic import validators

not_empty = toolkit.get_validator('not_empty')
ignore_missing = toolkit.get_validator('ignore_missing')
ignore_empty = toolkit.get_validator('ignore_empty')
positive_integer = toolkit.get_validator('is_positive_integer')


def mssql():
    return {
        'db_name': [not_empty, unicode],
        'host': [not_empty, unicode],
        'port': [not_empty, positive_integer, unicode],
        'username': [not_empty, unicode],
        'password': [not_empty, unicode],
        'sql': [not_empty, unicode]
    }
