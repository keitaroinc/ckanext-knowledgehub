import logging

import ckan.logic as logic
from ckan.plugins import toolkit
from ckan.common import _

from ckanext.knowledgehub.model import Theme
from ckanext.knowledgehub.model import SubThemes


log = logging.getLogger(__name__)

check_access = logic.check_access
ValidationError = logic.ValidationError
NotAuthorized = logic.NotAuthorized
NotFound = logic.NotFound


def theme_delete(context, data_dict):
    '''
    Deletes existing analytical
    framework Theme by id
    :param id
    '''
    check_access('theme_delete', context)

    if 'id' not in data_dict:
        raise ValidationError({"id": "Missing parameter"})

    Theme.delete({'id': data_dict['id']})

    return {"message": ["Theme deleted."]}


@toolkit.side_effect_free
def sub_theme_delete(context, data_dict):
    ''' Deletes a sub-theme

    :param id: the sub-theme's ID
    :type id: string

    :returns: OK
    :rtype: string
    '''

    try:
        check_access('sub_theme_delete', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system '
                              u'administrator to administer'))

    id = logic.get_or_bust(data_dict, 'id')
    try:
        filter = {'id': id}
        SubThemes.delete(filter)
    except NotFound:
        raise NotFound(_(u'Sub-theme'))

    return 'OK'
