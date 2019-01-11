import logging

import ckan.logic as logic
from ckanext.knowledgehub.model.theme import Theme


log = logging.getLogger(__name__)

check_access = logic.check_access
ValidationError = logic.ValidationError


def theme_delete(context, data_dict):
    '''
    Deletes existing analytical
    framework Theme by id
    :param id
    '''
    check_access('theme_delete', context)

    if 'id' not in data_dict:
        raise ValidationError({"id": "Missing parameter"})

    Theme.delete(data_dict['id'])

    return {"message": "Theme deleted."}
