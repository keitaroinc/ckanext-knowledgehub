import logging
import datetime
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as df

from ckanext.knowledgehub.logic import schema
from ckanext.knowledgehub.model import _table_dictize as td
from ckanext.knowledgehub.model.theme import Theme


log = logging.getLogger(__name__)

check_access = logic.check_access
check_access = logic.check_access
NotFound = logic.NotFound
ValidationError = logic.ValidationError


def theme_create(context, data_dict):
    '''
    Create new analytical framework Theme

        :param name
        :param title
        :param description
    '''
    check_access('theme_create', context)

    if 'name' not in data_dict:
        raise ValidationError({"name": "Missing parameter"})

    # we need the theme name in the context for name validation
    context['theme'] = data_dict['name']
    session = context['session']
    data, errors = df.validate(data_dict, schema.theme_schema(),
                               context)

    if errors:
        raise ValidationError(errors)

    theme = Theme()

    items = ['name', 'title', 'description']

    for item in items:
        setattr(theme, item, data.get(item))

    theme.created = datetime.datetime.utcnow()
    theme.modified = datetime.datetime.utcnow()
    theme.save()

    session.add(theme)
    session.commit()

    return td(theme, context)
