import logging
import datetime
import os

from sqlalchemy import exc
from psycopg2 import errorcodes as pg_errorcodes
from sqlalchemy import func
from werkzeug.datastructures import FileStorage as FlaskFileStorage

from ckan import logic
from ckan.common import _
from ckan.plugins import toolkit
from ckan import lib
from ckan import model
from ckan.logic.action.create import resource_create as ckan_rsc_create
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save

from ckanext.knowledgehub.logic import schema as knowledgehub_schema
from ckanext.knowledgehub.model.theme import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.model import Dashboard
from ckanext.knowledgehub.backend.factory import get_backend
from ckanext.knowledgehub.lib.writer import WriterService


log = logging.getLogger(__name__)

_df = lib.navl.dictization_functions
_table_dictize = lib.dictization.table_dictize
check_access = toolkit.check_access
_get_or_bust = logic.get_or_bust
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
        raise ValidationError({"name": _('Missing value')})

    user = context['user']
    session = context['session']

    # we need the old theme name in the context for name validation
    context['theme'] = None
    data, errors = _df.validate(data_dict, knowledgehub_schema.theme_schema(),
                                context)

    if errors:
        raise ValidationError(errors)

    theme = Theme()

    items = ['name', 'title', 'description']

    for item in items:
        setattr(theme, item, data.get(item))

    theme.created_at = datetime.datetime.utcnow()
    theme.modified_at = datetime.datetime.utcnow()
    theme.author = user

    if user:
        user_obj = model.User.by_name(user.decode('utf8'))
        if user_obj:
            theme.author_email = user_obj.email

    theme.save()

    session.add(theme)
    session.commit()

    return _table_dictize(theme, context)


@toolkit.side_effect_free
def sub_theme_create(context, data_dict):
    ''' Creates a new sub-theme

    :param title: title of the sub-theme
    :type title: string
    :param name: name of the sub-theme
    :type name: string
    :param description: a description of the sub-theme (optional)
    :type description: string
    :param theme: the ID of the theme
    :type theme: string

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

    st = SubThemes(**data)
    st.save()

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

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.research_question_schema(),
                                context)

    if errors:
        raise toolkit.ValidationError(errors)

    user_obj = context.get('auth_user_obj')
    user_id = user_obj.id

    theme = data.get('theme')
    sub_theme = data.get('sub_theme')
    url_slug = data.get('name')

    title = data.get('title')
    image_url = data.get('image_url')
    state = data.get('state', 'active')
    # FIXME if theme or subtheme id not exists, return notfound
    research_question = ResearchQuestion(
        name=url_slug,
        theme=theme,
        sub_theme=sub_theme,
        title=title,
        image_url=image_url,
        author=user_id,
        state=state
    )
    research_question.save()

    return _table_dictize(research_question, context)


def resource_create(context, data_dict):
    '''Override the existing resource_create to
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
    if 'research_question' in data_dict and \
            type(data_dict['research_question']) is list:
        data_dict['research_question'] = ','. \
            join(data_dict['research_question'])
    #     TODO we might need to get appropriate Themes and Sub-themes
    #      for the chosen research questions and add them
    #      to the solr index

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

            print('FIELDS: %s' % data.get('fields'))
            filename = '{}_{}.{}'.format(
                data_dict.get('db_type'),
                str(datetime.datetime.utcnow()),
                'csv'
            )

            if not data_dict.get('name'):
                data_dict['name'] = filename

            data_dict['upload'] = FlaskFileStorage(stream, filename)

    ckan_rsc_create(context, data_dict)


# Overwrite of the original 'resource_view_create'
# action in order to allow saving
# different types of resource views
def resource_view_create(context, data_dict):
    '''Creates a new resource view.

    :param resource_id: id of the resource
    :type resource_id: string
    :param title: the title of the view
    :type title: string
    :param description: a description of the view (optional)
    :type description: string
    :param view_type: type of view
    :type view_type: string
    :param config: options necessary to recreate a view state (optional)
    :type config: JSON string

    :returns: the newly created resource view
    :rtype: dictionary

    '''
    model = context['model']

    resource_id = _get_or_bust(data_dict, 'resource_id')

    schema = knowledgehub_schema.resource_view_schema()

    data, errors = _df.validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    check_access('resource_view_create', context, data_dict)

    max_order = model.Session.query(
        func.max(model.ResourceView.order)
    ).filter_by(resource_id=resource_id).first()

    order = 0
    if max_order[0] is not None:
        order = max_order[0] + 1
    data['order'] = order

    resource_view = model_save.resource_view_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit()
    return model_dictize.resource_view_dictize(resource_view, context)


def dashboard_create(context, data_dict):
    '''
    Create new dashboard

        :param name
        :param title
        :param description
        :param type
        :param source
        :param indicators
    '''
    check_access('dashboard_create', context)

    session = context['session']

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.dashboard_schema(),
                                context)

    if errors:
        raise ValidationError(errors)

    dashboard = Dashboard()

    items = ['name', 'title', 'description', 'type']

    for item in items:
        setattr(dashboard, item, data.get(item))

    dashboard.created_at = datetime.datetime.utcnow()
    dashboard.modified_at = datetime.datetime.utcnow()

    source = data.get('source')
    indicators = data.get('indicators')

    if source is not None:
        dashboard.source = source

    if indicators is not None:
        dashboard.indicators = indicators

    user = context.get('user')
    dashboard.created_by = model.User.by_name(user.decode('utf8')).id

    dashboard.save()

    session.add(dashboard)
    session.commit()

    return _table_dictize(dashboard, context)
