import logging
import datetime

from sqlalchemy import exc
from psycopg2 import errorcodes as pg_errorcodes

import ckan.logic as logic
from ckan.common import _
from ckan.plugins import toolkit
from ckan import lib
from ckan import model

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
NotAuthorized = toolkit.NotAuthorized


def theme_create(context, data_dict):
    '''
    Create new analytical framework Theme

        :param name
        :param title
        :param description
    '''
    check_access('theme_create', context)

    if 'name' not in data_dict:
        raise ValidationError({"name": ["Missing value"]})

    # we need the theme name in the context for name validation
    context['theme'] = data_dict['name']
    session = context['session']
    data, errors = _df.validate(data_dict, knowledgehub_schema.theme_schema(),
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

    return _table_dictize(theme, context)


@toolkit.side_effect_free
def sub_theme_create(context, data_dict):
    ''' Creates a new sub-theme

    :param name: name of the sub-theme
    :type name: string
    :param description: a description of the sub-theme (optional)
    :type description: string
    :param theme_id: the ID of the theme
    :type theme_id: string

    :returns: the newly created sub-theme
    :rtype: dictionary
    '''

    try:
        check_access('sub_theme_create', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system '
                              u'administrator to administer'))

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.sub_theme_create(),
                                context)
    if errors:
        raise ValidationError(errors)

    user = context.get('user')
    data['created_by'] = model.User.by_name(user.decode('utf8')).id

    try:
        st = SubThemes(**data)
        st.save()
    except exc.IntegrityError as e:
        if e.orig.pgcode == pg_errorcodes.UNIQUE_VIOLATION:
            raise ValidationError({
                    'name': ['Already exists']
                })
        raise

    return st.as_dict()

def research_question_create(context, data_dict):
    '''Create new research question.

    :param content: The research question.
    :type content: string
    :param theme: Theme of the research question.
    :type value: string
    :param sub_theme: SubTheme of the research question.
    :type value: string
    :param state: State of the research question. Default is active.
    :type state: string
    '''
    check_access('research_question_create', context, data_dict)

    data, errors = _df.validate(data_dict, knowledgehub_schema.research_question_schema(), context)

    if errors:
        raise toolkit.ValidationError(errors)

    user_obj = context.get('auth_user_obj')
    user_id = user_obj.id

    theme = data.get('theme')
    sub_theme = data.get('sub_theme')
    content = data.get('content')
    state = data.get('state', 'active')

    research_question = ResearchQuestion(
        theme=theme,
        sub_theme=sub_theme,
        content=content,
        author=user_id,
        state=state
    )
    research_question.save()

    return _table_dictize(research_question, context)
