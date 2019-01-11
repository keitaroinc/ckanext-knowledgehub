from ckan.plugins import toolkit
from ckan.common import _
from ckan import logic

from ckanext.knowledgehub.model import SubThemes


@toolkit.side_effect_free
def sub_theme_delete(context, data_dict):
    ''' Deletes a sub-theme

    :param id: the sub-theme's ID
    :type name: string

    :returns: OK
    :rtype: string
    '''

    try:
        logic.check_access('sub_theme_delete', context, data_dict)
    except logic.NotAuthorized:
        raise logic.NotAuthorized(_(u'Need to be system administrator to administer'))

    id = logic.get_or_bust(data_dict, 'id')
    try:
        filter = {'id': id}
        SubThemes.delete(filter)
    except logic.NotFound:
        raise logic.NotFound(_(u'Sub-theme'))

    return 'OK'