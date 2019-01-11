import logging

import ckan.logic as logic
from ckan.plugins import toolkit
from ckan.common import _

from ckanext.knowledgehub.model import _table_dictize as td
from ckanext.knowledgehub.model.theme import Theme


log = logging.getLogger(__name__)

check_access = logic.check_access
NotFound = logic.NotFound
ValidationError = logic.ValidationError


@toolkit.side_effect_free
def theme_show(context, data_dict):
    '''
        Returns existing analytical
        framework Theme
        :param id
        '''

    check_access('theme_update', context)

    if 'id' not in data_dict:
        raise ValidationError({"id": "Missing parameter"})

    theme = Theme.get(id=data_dict['id'])

    if not theme:
        log.debug('Could not find theme %s', id)
        raise NotFound(_('Theme was not found.'))

    return td(theme, context)
