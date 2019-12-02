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
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
from ckan.logic.action.update import package_update as ckan_package_update

from ckanext.knowledgehub.logic import schema as knowledgehub_schema
from ckanext.knowledgehub.model.theme import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.model import Dashboard
from ckanext.knowledgehub.model import KWHData
from ckanext.knowledgehub.model import Visualization
from ckanext.knowledgehub.backend.factory import get_backend
from ckanext.knowledgehub.lib.writer import WriterService
from ckanext.knowledgehub import helpers as plugin_helpers


log = logging.getLogger(__name__)

_df = lib.navl.dictization_functions
_table_dictize = lib.dictization.table_dictize
_get_or_bust = logic.get_or_bust

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

    context['research_question_name'] = research_question.name
    context['research_question_title'] = research_question.title
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
    rq_data = rq.as_dict()

    # Update index
    ResearchQuestion.update_index_doc(rq_data)

    return rq_data


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


# Overwrite of the original 'resource_view_update'
# action in order to allow updating
# different types of resource views
def resource_view_update(context, data_dict):
    '''Update a resource view.

    To update a resource_view you must be authorized to update the resource
    that the resource_view belongs to.

    For further parameters see ``resource_view_create()``.

    :param id: the id of the resource_view to update
    :type id: string

    :returns: the updated resource_view
    :rtype: string

    '''
    model = context['model']
    id = _get_or_bust(data_dict, "id")

    resource_view = model.ResourceView.get(id)
    if not resource_view:
        raise NotFound

    schema = knowledgehub_schema.resource_view_schema()

    data, errors = _df.validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    context['resource_view'] = resource_view
    context['resource'] = model.Resource.get(resource_view.resource_id)
    # TODO need to implement custom authorization actions
    # check_access('resource_view_update', context, data_dict)

    resource_view = model_save.resource_view_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit()
    resource_view_data = model_dictize.resource_view_dictize(resource_view, context)

    # Update index
    Visualization.update_index_doc(resource_view_data)

    return resource_view_data


def dashboard_update(context, data_dict):
    '''
    Updates existing dashboard

        :param id
        :param name
        :param description
        :param title
        :param indicators
    '''
    check_access('dashboard_update', context)

    name_or_id = data_dict.get("id") or data_dict.get("name")

    if name_or_id is None:
        raise ValidationError({'id': _('Missing value')})

    dashboard = Dashboard.get(name_or_id)

    if not dashboard:
        log.debug('Could not find dashboard %s', name_or_id)
        raise NotFound(_('Dashboard was not found.'))

    # we need the old dashboard name in the context for name validation
    context['dashboard'] = dashboard.name
    session = context['session']
    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.dashboard_schema(),
                                context)
    if errors:
        raise ValidationError(errors)

    items = ['name', 'title', 'description', 'indicators', 'source', 'type']

    for item in items:
        setattr(dashboard, item, data.get(item))

    dashboard_type = data.get('type')
    if dashboard_type != 'external':
        dashboard.source = ''

    dashboard.modified_at = datetime.datetime.utcnow()
    dashboard.save()

    session.add(dashboard)
    session.commit()

    dashboard_data = _table_dictize(dashboard, context)

    # Update index
    Dashboard.update_index_doc(dashboard_data)

    return dashboard_data


def package_update(context, data_dict):
    research_questions = data_dict.get('research_question')
    rq_options = plugin_helpers.get_rq_options()
    rq_ids = []

    if research_questions:
        if isinstance(research_questions, list):
            for rq in research_questions:
                for rq_opt in rq_options:
                    if rq == rq_opt.get('text'):
                        rq_ids.append(rq_opt.get('id'))
                        break
            data_dict['research_question'] = rq_ids
        elif isinstance(research_questions, unicode):
            for rq in rq_options:
                if rq.get('text') == research_questions:
                    data_dict['research_question'] = [rq.get('id')]
                    break

    return ckan_package_update(context, data_dict)


def kwh_data_update(context, data_dict):
    '''
    Store Knowledge Hub data
        :param type
        :param old_content
        :param new_content
    '''
    check_access('kwh_data', context, data_dict)

    session = context['session']

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.kwh_data_schema_update(),
                                context)

    if errors:
        raise ValidationError(errors)

    user = context.get('user')
    data['user'] = model.User.by_name(user.decode('utf8')).id

    kwh_data = KWHData.get(
        user=data['user'],
        content=data['old_content'],
        type=data['type']
    ).first()

    if kwh_data:
        update_data = _table_dictize(kwh_data, context)
        update_data.pop('id')
        update_data.pop('created_at')
        update_data['content'] = data['new_content']

        filter = {'id': kwh_data.id}
        data = KWHData.update(filter, update_data)

        return data.as_dict()
