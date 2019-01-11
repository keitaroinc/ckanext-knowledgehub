import logging
import datetime


from ckan.common import _
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as df

from ckanext.knowledgehub.logic import schema
from ckanext.knowledgehub.model import _table_dictize as td
from ckanext.knowledgehub.model.theme import Theme


log = logging.getLogger(__name__)

check_access = logic.check_access
NotFound = logic.NotFound
ValidationError = logic.ValidationError


def theme_update(context, data_dict):
    '''
    Updates existing analytical framework Theme

        :param id
        :param name
        :param description
    '''
    check_access('theme_update', context)

    if 'id' not in data_dict:
        raise ValidationError({"id": "Missing parameter"})

    if 'name' not in data_dict:
        raise ValidationError({"name": "Missing parameter"})

    theme = Theme.get(id=data_dict['id'])

    if not theme:
        log.debug('Could not find theme %s', id)
        raise NotFound(_('Theme was not found.'))

    # we need the theme name in the context for name validation
    context['theme'] = data_dict['name']
    session = context['session']
    data, errors = df.validate(data_dict, schema.theme_schema(),
                               context)

    if errors:
        raise ValidationError(errors)

    if not theme:
        theme = Theme()

    items = ['name', 'title', 'description']

    for item in items:
        setattr(theme, item, data.get(item))

    theme.modified = datetime.datetime.utcnow()
    theme.save()

    session.add(theme)
    session.commit()

    return td(theme, context)
