import logging
import datetime

from sqlalchemy import exc
from psycopg2 import errorcodes as pg_errorcodes
from werkzeug.datastructures import FileStorage as FlaskFileStorage

from ckan.common import _
import ckan.logic as logic
from ckan.plugins import toolkit
from ckan import model
from ckan import lib
from ckan.logic.action.update import resource_update as ckan_rsc_update

from ckanext.knowledgehub.logic import schema as knowledgehub_schema
from ckanext.knowledgehub.model.theme import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.backend.factory import get_backend
from ckanext.knowledgehub.lib.writer import WriterService


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
    :param theme: the ID of the theme
    :type theme: string

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

    sub_theme = SubThemes.get(id_or_name=id).first()

    if not sub_theme:
        log.debug('Could not find theme %s', id)
        raise logic.NotFound(_('Sub-Theme was not found.'))

    context['sub_theme'] = sub_theme.name
    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.sub_theme_update(),
                                context)

    if errors:
        raise logic.ValidationError(errors)

    user = context.get('user')
    data_dict['modified_by'] = model.User.by_name(user.decode('utf8')).id

    filter = {'id': id}
    st = SubThemes.update(filter, data_dict)

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

    id = logic.get_or_bust(data_dict, 'id')
    data_dict.pop('id')

    research_question = ResearchQuestion.get(id_or_name=id).first()

    if not research_question:
        log.debug('Could not find research question %s', id)
        raise logic.NotFound(_('Research question not found.'))

    context['research_question'] = research_question.name
    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.research_question_schema(),
                                context)

    if errors:
        raise logic.ValidationError(errors)

    user = context.get('user')
    data['modified_by'] = model.User.by_name(user.decode('utf8')).id

    filter = {'id': id}
    data.pop('__extras', None)
    rq = ResearchQuestion.update(filter, data)
    return rq.as_dict()


def resource_update(context, data_dict):
    '''Override the existing resource_update to
    support data upload from data sources

    :param db_type: title of the sub-theme
    :type db_type: string

    ```MSSQL```
    :param host: hostname
    :type host: string
    :param port: the port
    :type port: int
    :param username: DB username
    :type username: string
    :param password: DB password
    :type password: string
    :param sql: SQL Query
    :type sql: string

    ```Validation```
    :param schema: schema to be used for validation
    :type schema: string
    :param validation_options: options to be used for validation
    :type validation_options: string
    '''

    if (data_dict['schema'] == ''):
        del data_dict['schema']

    if (data_dict['validation_options'] == ''):
        del data_dict['validation_options']

    if data_dict.get('db_type') is not None:
        if data_dict.get('db_type') == '':
            raise logic.ValidationError({
                'db_type': [_('Please select the DB Type')]
            })

        backend = get_backend(data_dict)
        backend.configure(data_dict)
        data = backend.search_sql(data_dict)

        if data.get('records', []):
            writer = WriterService()
            stream = writer.csv_writer(data.get('fields'),
                                       data.get('records'),
                                       ',')

            filename = data_dict.get('url')
            if not filename:
                filename = '{}_{}.{}'.format(
                    data_dict.get('db_type'),
                    str(datetime.datetime.utcnow()),
                    'csv'
                )

            data_dict['upload'] = FlaskFileStorage(stream, filename)

    ckan_rsc_update(context, data_dict)
