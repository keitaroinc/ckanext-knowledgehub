import logging
import datetime

from sqlalchemy import exc
from psycopg2 import errorcodes as pg_errorcodes

from ckan.common import _
import ckan.logic as logic
from ckan.plugins import toolkit
from ckan import model
from ckan import lib

from ckanext.knowledgehub.logic import schema as knowledgehub_schema
from ckanext.knowledgehub.model.theme import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion


log = logging.getLogger(__name__)

_df = lib.navl.dictization_functions
_table_dictize = lib.dictization.table_dictize

check_access = toolkit.check_access
NotFound = logic.NotFound
ValidationError = toolkit.ValidationError


def theme_update(context, data_dict):
    '''
    Updates existing analytical framework Theme

        :param id
        :param name
        :param description
    '''
    check_access('theme_update', context)

    name_or_id = data_dict.get("id") or data_dict.get("name")

    if name_or_id is None:
        raise ValidationError({'id': _('Missing value')})

    theme = Theme.get(name_or_id)

    if not theme:
        log.debug('Could not find theme %s', name_or_id)
        raise NotFound(_('Theme was not found.'))

    # we need the old theme name in the context for name validation
    context['theme'] = theme.name
    session = context['session']
    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.theme_schema(),
                                context)
    if errors:
        raise ValidationError(errors)

    if not theme:
        theme = Theme()

    items = ['name', 'title', 'description']

    for item in items:
        setattr(theme, item, data.get(item))

    theme.modified_at = datetime.datetime.utcnow()
    theme.save()

    session.add(theme)
    session.commit()

    return _table_dictize(theme, context)


@toolkit.side_effect_free
def sub_theme_update(context, data_dict):
    ''' Updates an existing sub-theme

    :param name: name of the sub-theme
    :type name: string
    :param description: a description of the sub-theme (optional)
    :type description: string
    :param theme_id: the ID of the theme
    :type theme_id: string

    :returns: the updated sub-theme
    :rtype: dictionary
    '''

    try:
        logic.check_access('sub_theme_update', context, data_dict)
    except logic.NotAuthorized:
        raise logic.NotAuthorized(_(u'Need to be system '
                                    u'administrator to administer'))

    id = logic.get_or_bust(data_dict, 'id')
    data_dict.pop('id')

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.sub_theme_update(),
                                context)
    if errors:
        raise logic.ValidationError(errors)

    user = context.get('user')
    data_dict['modified_by'] = model.User.by_name(user.decode('utf8')).id

    try:
        filter = {'id': id}
        st = SubThemes.update(filter, data_dict)
    except exc.IntegrityError as e:
        if e.orig.pgcode == pg_errorcodes.UNIQUE_VIOLATION:
            raise logic.ValidationError({
                    'name': ['Already exists']
                })
        raise

    return st.as_dict()


def research_question_update(context, data_dict):
    '''Update research question.

    :param content: The research question.
    :type content: string
    :param theme: Theme of the research question.
    :type value: string
    :param sub_theme: SubTheme of the research question.
    :type value: string
    :param state: State of the research question. Default is active.
    :type state: string
    '''
    check_access('research_question_update', context)

    from pprint import pprint as pprint
    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.research_question_schema(),
                                context)

    if errors:
        raise toolkit.ValidationError(errors)

    id = data.get('id')
    theme = data.get('theme')
    sub_theme = data.get('sub_theme')
    content = data.get('content')

    session = context['session']

    rq = ResearchQuestion.get(id=id).first()

    rq.theme = theme
    rq.sub_theme = sub_theme
    rq.content = content
    rq.modified = datetime.datetime.now()
    rq.save()
    session.add(rq)
    session.commit()
    return _table_dictize(rq, context)
