import logging
import datetime
import os
import subprocess
import re

from sqlalchemy import exc
from psycopg2 import errorcodes as pg_errorcodes
from sqlalchemy import func
from werkzeug.datastructures import FileStorage as FlaskFileStorage

from hdx.utilities.easy_logging import setup_logging
from hdx.data.dataset import Dataset
from hdx.data.resource import Resource

from ckan import logic
from ckan.common import _, g, config
from ckan.plugins import toolkit
from ckan import lib
from ckan import model
from ckan.logic.action.create import resource_create as ckan_rsc_create
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
from ckan.logic.action.create import (
    package_create as ckan_package_create,
)
from ckan.lib.helpers import url_for, render_markdown

from ckanext.knowledgehub.logic import schema as knowledgehub_schema
from ckanext.knowledgehub.logic.action.get import user_query_show
from ckanext.knowledgehub.model.theme import Theme
from ckanext.knowledgehub.model import (
    AccessRequest,
    AssignedAccessRequest,
    SubThemes,
    ResearchQuestion,
    Dashboard,
    ResourceFeedbacks,
    ResourceValidate,
    ResourceValidation,
    KWHData,
    RNNCorpus,
    Visualization,
    UserIntents,
    UserQuery,
    UserQueryResult,
    Keyword,
    UserProfile,
    ExtendedTag,
    Notification,
    Posts,
    Comment,
)
from ckanext.knowledgehub.backend.factory import get_backend
from ckanext.knowledgehub.lib.writer import WriterService
from ckanext.knowledgehub import helpers as plugin_helpers
from ckanext.knowledgehub.lib.profile import user_profile_service
from ckanext.knowledgehub.lib.util import get_as_list
from ckanext.knowledgehub.logic.jobs import (
    schedule_update_index,
    schedule_notification_email,
    schedule_broadcast_notification_email,
)

log = logging.getLogger(__name__)

_df = lib.navl.dictization_functions
_table_dictize = lib.dictization.table_dictize
check_access = toolkit.check_access
get_action = toolkit.get_action
_get_or_bust = logic.get_or_bust
NotFound = logic.NotFound
ValidationError = toolkit.ValidationError
NotAuthorized = toolkit.NotAuthorized
Invalid = _df.Invalid


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

    theme_data = _table_dictize(theme, context)

    # Add to kwh data
    try:
        data_dict = {
            'type': 'theme',
            'title': theme_data.get('title'),
            'description': theme_data.get('description'),
            'theme': theme_data.get('id')
        }
        logic.get_action('kwh_data_create')(context, data_dict)
    except Exception as e:
        log.debug('Unable to store theme {} to knowledgehub data: {}'.format(
            theme_data.get('id'), str(e)
        ))

    return theme_data


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

    sub_theme_data = st.as_dict()

    # Add to kwh data
    try:
        data_dict = {
            'type': 'sub_theme',
            'title': sub_theme_data.get('title'),
            'description': sub_theme_data.get('description'),
            'sub_theme': sub_theme_data.get('id')
        }
        logic.get_action('kwh_data_create')(context, data_dict)
    except Exception as e:
        log.debug(
            'Unable to store sub-theme {} to knowledgehub data: {}'.format(
                sub_theme_data.get('id'),
                str(e)))

    return sub_theme_data


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
    name = data.get('name')

    title = data.get('title')
    image_url = data.get('image_url')
    state = data.get('state', 'active')
    modified_at = datetime.datetime.utcnow()
    # FIXME if theme or subtheme id not exists, return notfound
    research_question = ResearchQuestion(
        name=name,
        theme=theme,
        sub_theme=sub_theme,
        title=title,
        image_url=image_url,
        author=user_id,
        state=state,
        modified_at=modified_at
    )

    tags = data_dict.get('tags', '')
    if tags:
        for tag in tags.split(','):
            try:
                check_access('tag_show', context)
                tag_obj = toolkit.get_action('tag_show')(context, {'id': tag})
            except logic.NotFound:
                check_access('tag_create', context)
                tag_obj = toolkit.get_action('tag_create')(context, {
                    'name': tag,
                })

        research_question.tags = tags

    research_question.save()

    research_question_data = _table_dictize(research_question, context)
    # Add to index
    try:
        ResearchQuestion.add_to_index(research_question_data)
    except Exception as e:
        ResearchQuestion.delete(research_question.id)
        raise e

    # Add to kwh data
    try:
        data_dict = {
            'type': 'research_question',
            'title': research_question_data.get('title'),
            'research_question': research_question_data.get('id')
        }
        logic.get_action('kwh_data_create')(context, data_dict)
    except Exception as e:
        log.debug(
            'Unable to store research question %s to knowledgehub data: %s' %
            (research_question_data.get('id'), str(e))
        )

    return research_question_data


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
    if (data_dict.get('schema') == ''):
        del data_dict['schema']

    if (data_dict.get('validation_options') == ''):
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

            filename = '{}_{}.{}'.format(
                data_dict.get('db_type'),
                str(datetime.datetime.utcnow()),
                'csv'
            )

            if not data_dict.get('name'):
                data_dict['name'] = filename

            data_dict['upload'] = FlaskFileStorage(stream, filename)

    create_resource_kwh = ckan_rsc_create(context, data_dict)

    if (data_dict.get('admin')):
        plugin_helpers.resource_validation_notification(
            context['auth_user_obj'],
            data_dict,
            plugin_helpers.Entity.Resource
        )

    return create_resource_kwh


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
    # TODO need to implement custom authorization actions
    # check_access('resource_view_create', context, data_dict)

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
    rv_data = model_dictize.resource_view_dictize(resource_view, context)

    # Add to index
    Visualization.add_to_index(rv_data)

    # Add to kwh data
    try:
        data_dict = {
            'type': 'visualization',
            'title': rv_data.get('title'),
            'description': rv_data.get('description'),
            'visualization': rv_data.get('id')
        }
        logic.get_action('kwh_data_create')(context, data_dict)
    except Exception as e:
        log.debug(
            'Unable to store visualization %s to knowledgehub data: %s' %
            (rv_data.get('id'), str(e))
        )

    # this check is because of the unit tests
    if rv_data.get('__extras'):
        ext = rv_data['__extras']
        if ext.get('research_questions'):
            plugin_helpers.add_rqs_to_dataset(context, rv_data)

    return rv_data


def dashboard_create(context, data_dict):
    '''
    Create new dashboard

        :param name
        :param title
        :param description
        :param type
        :param source
        :param indicators
        :param tags
    '''
    check_access('dashboard_create', context)
    session = context['session']

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.dashboard_schema(),
                                context)

    if errors:
        raise ValidationError(errors)

    dashboard = Dashboard()

    items = ['name', 'title', 'description', 'type', 'tags']

    for item in items:
        setattr(dashboard, item, data.get(item))

    dashboard.created_at = datetime.datetime.utcnow()
    dashboard.modified_at = datetime.datetime.utcnow()

    source = data.get('source')
    indicators = data.get('indicators')
    datasets = data_dict.get('datasets')
    shared_with_users = data_dict.get('shared_with_users')
    shared_with_organizations = get_as_list('shared_with_organizations',
                                            data_dict)
    shared_with_groups = get_as_list('shared_with_groups', data_dict)

    dashboard.shared_with_organizations = ','.join(shared_with_organizations)
    dashboard.shared_with_groups = ','.join(shared_with_groups)

    if source is not None:
        dashboard.source = source

    if indicators is not None:
        dashboard.indicators = indicators

    if datasets is not None:
        if isinstance(datasets, unicode):
            dashboard.datasets = datasets
        elif isinstance(datasets, list):
            dashboard.datasets = ', '.join(datasets)

    if shared_with_users is not None:
        if isinstance(shared_with_users, list):
            dashboard.shared_with_users = ','.join(shared_with_users)
        else:
            dashboard.shared_with_users = shared_with_users

    tags = data_dict.get('tags', '')
    if tags:
        for tag in tags.split(','):
            try:
                check_access('tag_show', context)
                tag_obj = toolkit.get_action('tag_show')(context, {'id': tag})
            except logic.NotFound:
                check_access('tag_create', context)
                tag_obj = toolkit.get_action('tag_create')(context, {
                    'name': tag,
                })

        dashboard.tags = tags

    user = context.get('user')
    dashboard.created_by = model.User.by_name(user.decode('utf8')).id

    dashboard.save()

    session.add(dashboard)
    session.commit()

    dashboard_data = _table_dictize(dashboard, context)

    # Add to index
    Dashboard.add_to_index(dashboard_data)

    # Send notification for sharing with users
    if shared_with_users is not None:
        if isinstance(shared_with_users, unicode):
            shared_with_users = shared_with_users.split()

        plugin_helpers.shared_with_users_notification(
            context['auth_user_obj'],
            shared_with_users,
            dashboard_data,
            plugin_helpers.Entity.Dashboard,
            plugin_helpers.Permission.Granted
        )
        for recipient in shared_with_users:
            schedule_notification_email(
                user,
                'notification_access_granted',
                {
                    'type': 'dashboard',
                    'dashboard': dashboard_data,
                })

    # Add to kwh data
    try:
        kwh_data = {
            'type': 'dashboard',
            'title': dashboard_data.get('title'),
            'description': dashboard_data.get('description'),
            'dashboard': dashboard_data.get('id')
        }
        logic.get_action('kwh_data_create')(context, kwh_data)
    except Exception as e:
        log.debug(
            'Unable to store dashboard %s to knowledgehub data: %s' %
            (dashboard_data.get('id'), str(e))
        )

    def _notification(_type):
        return {
            'title': _('Permission granted'),
            'description': _('The dashboard {} have been '
                             'shared with your {}.').format(dashboard.title,
                                                            _type),
            'link': url_for('dashboards_view', name=dashboard.name),
        }

    for _type, groups in [('organization', shared_with_organizations),
                          ('group', shared_with_groups)]:
        plugin_helpers.notification_broadcast({
            'ignore_auth': True,
            'auth_user_obj': context.get('auth_user_obj'),
        }, _notification(_type), groups)
        # schedule emails
        for group_id in groups:
            schedule_broadcast_notification_email(
                group_id,
                'notification_access_granted',
                {
                    'type': 'dashboard',
                    'group_id': group_id,
                    'group_type': _type,
                    'dashboard': dashboard,
                })
    return dashboard_data


def package_create(context, data_dict):
    shared_with_users = get_as_list('shared_with_users', data_dict)
    shared_with_groups = get_as_list('shared_with_groups', data_dict)
    shared_with_organizations = get_as_list('shared_with_organizations',
                                            data_dict)

    # Remap to comma separated values
    data_dict['shared_with_users'] = ','.join(shared_with_users)
    data_dict['shared_with_organizations'] = \
        ','.join(shared_with_organizations)
    data_dict['shared_with_groups'] = ','.join(shared_with_groups)

    dataset = ckan_package_create(context, data_dict)

    if shared_with_users:
        plugin_helpers.shared_with_users_notification(
            context['auth_user_obj'],
            shared_with_users,
            dataset,
            plugin_helpers.Entity.Dataset,
            plugin_helpers.Permission.Granted
        )

        for user_id in shared_with_users:
            schedule_notification_email(
                user_id,
                'notification_access_granted',
                {
                    'type': 'package',
                    'package': dataset,
                })

    plugin_helpers.notification_broadcast({
        'ignore_auth': True,
        'auth_user_obj': context.get('auth_user_obj'),
    }, {
        'title': _('Access granted to dataset'),
        'description': _('You have been granted '
                         'access to {}').format(dataset['title']),
        'link': url_for(controller='package', action='read', id=dataset['id'])
    }, shared_with_groups + shared_with_organizations)

    for group_id in shared_with_groups:
        schedule_broadcast_notification_email(
            group_id,
            'notification_access_granted',
            {
                'type': 'package',
                'package': dataset,
                'group_id': group_id,
                'group_type': 'group',
            })
    for group_id in shared_with_organizations:
        schedule_broadcast_notification_email(
            group_id,
            'notification_access_granted',
            {
                'type': 'package',
                'package': dataset,
                'group_id': group_id,
                'group_type': 'organization',
            })

    try:
        data_dict = {
            'type': 'dataset',
            'title': dataset.get('title'),
            'description': dataset.get('notes'),
            'dataset': dataset.get('id')
        }
        logic.get_action('kwh_data_create')(context, data_dict)
    except Exception as e:
        log.debug(
            'Unable to store dataset %s to knowledgehub data: %s' %
            (dataset.get('id'), str(e))
        )

    return dataset


def resource_feedback(context, data_dict):
    '''
    Resource feedback mechanism

        :param type
        :param dataset
        :param resource
    '''
    check_access('resource_feedback', context, data_dict)

    session = context['session']

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.resource_feedback_schema(),
                                context)

    if errors:
        raise ValidationError(errors)

    user = context.get('user')
    data['user'] = model.User.by_name(user.decode('utf8')).id
    resource = data.get('resource')
    oppisite_rf = {
        'useful': 'unuseful',
        'unuseful': 'useful',
        'trusted': 'untrusted',
        'untrusted': 'trusted'
    }

    rf = ResourceFeedbacks.get(
        user=data['user'],
        resource=resource,
        type=oppisite_rf[data['type']]
    ).first()

    if not rf:
        rf = ResourceFeedbacks(**data)
        rf.save()
        return rf.as_dict()
    else:
        filter = {'id': rf.id}
        rf = ResourceFeedbacks.update(filter, data)

        return rf.as_dict()


def resource_validation_create(context, data_dict):
    '''
    Resource validation mechanism

        :param dataset
        :param resource
        :param user
        :param admin
        :param admin_email
        :param status
    '''
    check_access('resource_validation_create', context, data_dict)

    resource_schema = knowledgehub_schema.resource_validation_schema()
    data, errors = _df.validate(data_dict,
                                resource_schema,
                                context)

    if errors:
        raise ValidationError(errors)

    usr = context.get('user')

    dataset = data_dict.get('package_id')
    resource = data_dict.get('id')
    resource_url = url_for(
        controller='package',
        action='resource_read',
        id=dataset,
        resource_id=resource,
        qualified=True
    )
    status = 'not_validated'

    if data.get('admin'):
        user = model.User.by_name(usr.decode('utf8')).id
        admin = data.get('admin')
        admin_email = model.User.by_name(admin).email
        requested_at = datetime.datetime.utcnow()

        rv = ResourceValidation(
            dataset=dataset,
            resource=resource,
            resource_url=resource_url,
            user=user,
            admin=admin,
            admin_email=admin_email,
            status=status,
            requested_at=requested_at,
            notification_sent=True
        )

        rv.save()
        return _table_dictize(rv, context)
    else:
        rv = ResourceValidation(
            dataset=dataset,
            resource=resource,
            resource_url=resource_url,
            status=status
        )

        rv.save()
        return _table_dictize(rv, context)


@toolkit.side_effect_free
def kwh_data_create(context, data_dict):
    ''' Store Knowledge Hub data needed for predictove search.
    It keeps the title and description of KWH entities: themes, sub-themes,
    research questions, datasets, visualizations and dashboards.

    :param type: the type of the entity, can be:
    [
        'search_query',
        'theme',
        'sub_theme',
        'research_question',
        'dataset',
        'visualization',
        'dashboard'
    ]
    :type type: string
    :param title: the title of the entity
    :type title: string
    :param description: the description of the entity (optional)
    :type description: string
    :param theme: the ID of th theme (optional)
    :type theme: string
    :param sub_theme: the ID of the sub theme (optional)
    :type sub_theme: string
    :param research_question: the ID of the research question (optional)
    :type research_question: string
    :param dataset: the ID of the dataset (optional)
    :type dataset: string
    :param visualization: the ID of the visualization (optional)
    :type visualization: string
    :param dashboard: the ID of the dashboard (optional)
    :type dashboard: string

    returns: the newly created data
    :rtype: dict
    '''

    session = context['session']

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.kwh_data_schema(),
                                context)

    if errors:
        raise ValidationError(errors)

    user = context.get('user')
    if user:
        data['user'] = model.User.by_name(user.decode('utf8')).id

    kwh_data = KWHData.get(
        user=data.get('user'),
        type=data.get('type'),
        title=data.get('title'),
        description=data.get('description'),
    ).first()

    if not kwh_data:
        kwh_data = KWHData(**data)
        kwh_data.save()

    return kwh_data.as_dict()


def corpus_create(context, data_dict):
    '''
    Store RNN corpus
        :param corpus
    '''
    check_access('corpus_create', context, data_dict)

    session = context['session']

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.corpus_create(),
                                context)

    if errors:
        raise ValidationError(errors)

    corpus = RNNCorpus(**data)
    corpus.save()
    return corpus.as_dict()


def run_command(context, data_dict):
    '''
        This action is only intendet to be used for running scripts as
        cron jobs.

        :param command: the command the will be executed such a `db int`
        :type title: string

        :returns: OK
        :rtype: string
    '''

    check_access('run_command', context, data_dict)

    command = _get_or_bust(data_dict, 'command')

    try:
        ckan_ini = os.environ.get('CKAN_INI', '/srv/app/production.ini')
        cmd_args = command.split(' ')
        cmd = ['knowledgehub', '-c', ckan_ini]
        for c in cmd_args:
            cmd.append(c)

        subprocess.call(cmd)
    except Exception as e:
        return 'Error: %s' % str(e)

    return 'Successfully run command: %s' % ' '.join(cmd)


def user_intent_create(context, data_dict):
    ''' Creates a new intent

    :param user_query_id: the ID of the user query
    :type user_query_id: string
    :param primary_category: the category of the intent (optional)
    :type primary_category: styring
    :param theme: the ID of the theme (optional)
    :type theme: string
    :param sub_theme: the ID of the sub-theme (optional)
    :type sub_theme: string
    :param research_question: the ID of the research question (optional)
    :type research_question: string
    :param inferred_transactional: the intent of transactional
    searching (optional)
    :type inferred_transactional: string
    :param inferred_navigational: the intent of naviagational
    searching (optional)
    :type inferred_navigational: string
    :param inferred_informational: the intent of informational
    searching (optional)
    :type inferred_informational: string
    :param curated: indicate whether the classification is curated (optional)
    :type curated: bool
    :param accurate: indicate whether the classification is accurate (optional)
    :type accurate: bool

    :returns: the newly created intent
    :rtype: dictionary
    '''

    try:
        check_access('user_intent_create', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system '
                              u'administrator to administer'))

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.user_intent_schema(),
                                context)
    if errors:
        raise ValidationError(errors)

    user = context.get('user')
    if user:
        data['user_id'] = model.User.by_name(user.decode('utf8')).id

    intent = UserIntents(**data)
    intent.save()

    return intent.as_dict()


def user_query_create(context, data_dict):
    ''' Save user query

    :param query_text: the user search query
    :type query_text: string
    :param query_type: the type of the search query
    :type query_type: string

    :returns: the newly created user query
    :rtype:dictionary
    '''

    try:
        check_access('user_query_create', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system '
                              u'administrator to administer'))

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.user_query_schema(),
                                context)
    if errors:
        raise ValidationError(errors)

    user = context.get('user')
    if user:
        data['user_id'] = model.User.by_name(user.decode('utf8')).id

    def save_user_query(data):
        query = UserQuery(**data)
        query.save()
        return query.as_dict()

    if data.get('user_id'):
        try:
            query = user_query_show(
                context,
                {
                    'query_text': data.get('query_text'),
                    'query_type': data.get('query_type'),
                    'user_id': data.get('user_id')
                }
            )

            raise Invalid(_('User query already exists'))
        except NotFound:
            return save_user_query(data)

    return save_user_query(data)


def user_query_result_create(context, data_dict):
    ''' Save user query result

    :param query_id: the ID of the search query
    :type query_id: string
    :param result_type: the type of search (dataset, visualization,
    research_question etc)
    :type result_type: string
    :param result_id: the ID of the dataset/visualization/rq etc
    :type result_id: string

    :returns: the newly created user query result
    :rtype: dictionary
    '''

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.user_query_result_schema(),
                                context)
    if errors:
        raise ValidationError(errors)

    user = context.get('user')
    if user:
        data['user_id'] = model.User.by_name(user.decode('utf8')).id

    query_result = UserQueryResult(**data)
    query_result.save()

    return query_result.as_dict()


def merge_all_data(context, data_dict):
    u''' Merge data resources that belongs to the dataset and create
    new data resource with the whole data

    :param id: the dataset ID
    :type id: string

    :returns: the resource created/updated or error message
    :rtype: dict
    '''

    package_id = data_dict.get('id')

    if not package_id:
        raise ValidationError({'id': _('Missing value')})

    data_dict = plugin_helpers.get_dataset_data(package_id)

    if data_dict.get('records') and not data_dict.get('err_msg'):
        writer = WriterService()
        stream = writer.csv_writer(
            data_dict.get('fields'), data_dict['records'], ',')

        package_name = data_dict.get('package_name')
        filename = '{}_{}.{}'.format(
            package_name,
            str(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')),
            'csv'
        )

        rsc_dict = {
            'package_id': package_id,
            'name': '{}_{}'.format(
                package_name,
                plugin_helpers.SYSTEM_RESOURCE_TYPE
            ),
            'upload':  FlaskFileStorage(stream, filename),
            'resource_type': plugin_helpers.SYSTEM_RESOURCE_TYPE
        }

        if data_dict.get('system_resource'):
            rsc_dict['id'] = data_dict['system_resource']['id']
            rsc_dict['name'] = data_dict['system_resource']['name']
            toolkit.get_action('resource_update')(
                context, rsc_dict)
            return {}
        else:
            return toolkit.get_action('resource_create')(
                context, rsc_dict)

    return {
        'err_msg': data_dict['err_msg']
    }


def resource_validate_create(context, data_dict):
    '''
    Saves user validation report
        :param what
        :param resource
    '''

    check_access('resource_validate_create', context, data_dict)
    user = context['auth_user_obj']
    name = getattr(user, "fullname")

    if not name:
        name = context['user']

    session = context['session']

    context['resource_validate'] = None
    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.resource_validate_schema(),
                                context)

    if errors:
        raise ValidationError(errors)

    resource_validate = ResourceValidate()

    items = ['what']

    for item in items:
        setattr(resource_validate, item, data.get(item))

    resource_validate.when = datetime.datetime.utcnow().strftime(
        '%Y-%m-%dT%H:%M:%S'
    )
    resource_validate.who = name
    resource_validate.resource = data.get('resource')

    resource_validate.save()

    session.add(resource_validate)
    session.commit()

    return _table_dictize(resource_validate, context)


def member_create(context, data_dict=None):
    '''Make an object (e.g. a user, dataset or group) a member of a group.

    If the object is already a member of the group then the capacity of the
    membership will be updated.

    You must be authorized to edit the group.

    :param id: the id or name of the group to add the object to
    :type id: string
    :param object: the id or name of the object to add
    :type object: string
    :param object_type: the type of the object being added, e.g. ``'package'``
        or ``'user'``
    :type object_type: string
    :param capacity: the capacity of the membership
    :type capacity: string

    :returns: the newly created (or updated) membership
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create member object %s') \
            % data_dict.get('name', '')

    group_id, obj_id, obj_type, capacity = \
        _get_or_bust(data_dict, ['id', 'object', 'object_type', 'capacity'])

    group = model.Group.get(group_id)
    if not group:
        raise NotFound('Group was not found.')

    obj_class = logic.model_name_to_class(model, obj_type)
    obj = obj_class.get(obj_id)
    if not obj:
        raise NotFound('%s was not found.' % obj_type.title())

    check_access('member_create', context, data_dict)

    # Look up existing, in case it exists
    member = model.Session.query(model.Member).\
        filter(model.Member.table_name == obj_type).\
        filter(model.Member.table_id == obj.id).\
        filter(model.Member.group_id == group.id).\
        filter(model.Member.state == 'active').first()
    if not member:
        member = model.Member(table_name=obj_type,
                              table_id=obj.id,
                              group_id=group.id,
                              state='active')
        member.group = group
    member.capacity = capacity

    model.Session.add(member)
    model.repo.commit()

    if obj_type == 'package':
        plugin_helpers.views_dashboards_groups_update(data_dict.get('object'))

    return model_dictize.member_dictize(member, context)


def tag_create(context, data_dict):
    '''Create a new vocabulary tag.

    You must be a sysadmin to create vocabulary tags.

    You can use this function to create tags that belong to a vocabulary or
    to create a free tags that do not belong to any vocabulary.

    :param name: the name for the new tag, a string between 2 and 100
        characters long containing only alphanumeric characters and ``-``,
        ``_`` and ``.``, e.g. ``'Jazz'``
    :type name: string
    :param vocabulary_id: the id of the vocabulary that the new tag
        should be added to, e.g. the id of vocabulary ``'Genre'``
    :type vocabulary_id: string

    :returns: the newly-created tag
    :rtype: dictionary

    '''
    model = context['model']

    try:
        check_access('tag_create', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system '
                              u'administrator to administer'))

    schema = context.get('schema') or knowledgehub_schema.tag_create_schema()
    data, errors = _df.validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    tag = model_save.tag_dict_save(data_dict, context)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug("Created tag '%s' " % tag)
    tag.__class__ = ExtendedTag
    return model_dictize.tag_dictize(tag, context)


def keyword_create(context, data_dict):
    u'''Creates new keyword with name and tags.

    :param name: `str`, required, the name for the keyword
    :param tags: `list` of `str`, the names of the tags that this keyword
        contains. If a tag does not exist, it will be created.

    :returns: `dict`, the new keyword.
    '''
    check_access('keyword_create', context)
    if 'name' not in data_dict or not data_dict['name'].strip():
        raise ValidationError({'name': _('Missing Value')})

    data_dict['name'] = re.sub(r'\s+', '-', data_dict['name'].strip())

    existing = Keyword.by_name(data_dict['name'])
    if existing:
        raise ValidationError({
            'name': _('Keyword with that name already exists.')
        })

    keyword = Keyword(name=data_dict['name'])
    keyword.save()

    kwd_dict = _table_dictize(keyword, context)
    kwd_dict['tags'] = []
    for tag in data_dict.get('tags', []):
        try:
            check_access('tag_show', context)
            tag_dict = toolkit.get_action('tag_show')(context, {'id': tag})
        except logic.NotFound:
            check_access('tag_create', context)
            if context.get('tag'):
                context.pop('tag')
            tag_dict = toolkit.get_action('tag_create')(context, {
                'name': tag,
            })

        db_tag = ExtendedTag.get_with_keyword(tag_dict['id'])
        db_tag.keyword_id = keyword.id
        db_tag.save()
        tag_dict = _table_dictize(db_tag, context)
        kwd_dict['tags'].append(tag_dict)

        schedule_update_index(tag_dict['name'])

    return kwd_dict


def user_profile_create(context, data_dict):
    u'''Creates a user profile record for the currently authorized user.

    :param research_questions: `list`, list of research question ID's that are
        of interest.
    :param tags: `list`, list of tag ID's that are
        of interest.
    :param keywords: `list`, list of keyword ID's that are
        of interest.
    '''
    check_access('user_profile_create', context)

    username = None
    if hasattr(g, 'user'):
        username = g.user

    if not username:
        username = context.get('user')

    if not username:
        raise logic.NotAuthorized(_('Must be authroized to use this action'))

    user = toolkit.get_action('user_show')({
        'ignore_auth': True,
    }, {
        'id': username,
    })

    profile = UserProfile.by_user_id(user['id'])
    if profile:
        raise ValidationError({
            'user_id': _('Profile already created.')
        })

    profile = UserProfile(user_id=user['id'],
                          user_notified=False,
                          interests={})

    for interest_type in ['research_questions', 'keywords']:
        if data_dict.get(interest_type):
            profile.interests[interest_type] = data_dict[interest_type]

    profile.interests['tags'] = []
    for tag in data_dict.get('tags', []):
        try:
            tag = toolkit.get_action('tag_show')({
                'ignore_auth': True,
            }, {
                'id': tag,
            })
            profile.interests['tags'].append(tag['name'])
        except Exception as e:
            log.warning('Failed to load tag %s. Error: %s', tag, str(e))

    profile.save()
    model.Session.flush()

    try:
        user_profile_service.clear_cached(user['id'])
    except Exception as e:
        log.warning('Failed to delete cached data for user %s. Error: %s',
                    user['id'], str(e))

    profile_dict = _table_dictize(profile, context)
    return profile_dict


def user_query_result_save(context, data_dict):
    '''Saves the result of a query when a user clicks on a link.

    :param query_text: `str` the text of the query
    :param query_type: `str` the type of search query: dataset, dashboard etc.
    :param result_id: `str` the id of the selected object like dataset id,
        dashboard id etc.
    '''
    query_text = data_dict.get('query_text')
    query_type = data_dict.get('query_type')
    result_id = data_dict.get('result_id')
    user = context.get('auth_user_obj')
    if not (query_text and query_type and result_id and user):
        return {}  # just pass through, we don't have to generate error

    try:
        user_query = toolkit.get_action('user_query_show')({
            'ignore_auth': True,
        }, {
            'query_text': query_text,
            'query_type': query_type,
            'user_id': user.id,
        })

        user_query_result_create(context, {
            'query_id': user_query['id'],
            'result_type': query_type,
            'result_id': result_id,
        })
    except Exception as e:
        log.warning('Cannot fetch user_query. Error: %s', str(e))
        log.exception(e)

    try:
        kwh_data_create(context, {
            'type': 'search_query',
            'title': query_text,
        })
    except Exception as e:
        log.warning('Failed to store kwh_data. Error: %s', str(e))
        log.exception(e)

    return {}


def upsert_resource_to_hdx(context, data_dict):
    ''' Create new if not exists or update the existing resource in HDX

    :param resource_id: the ID of the resource in knowledgehub
    :type resource_id: string
    :param dataset_name: the name of the dataset in knowledgehub/HDX
    :type dataset_name: string
    :param hdx_rsc_name: the name of the resource in HDX that we want
        to update. If not present it will try to create new one (optional)
    :type hdx_rsc_name: string
    :returns: the created/updated resource
    :rtype: dict
    '''
    check_access('package_update', context)

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.hdx_resource(),
                                context)
    if errors:
        raise ValidationError(errors)

    try:
        dataset_name = data['dataset_name']
        dataset = Dataset.read_from_hdx(dataset_name)
        if not dataset:
            raise NotFound('Dataset %s does not exist in HDX' % dataset_name)

        rsc = get_action('resource_show')({'ignore_auth': True}, {
            'id': data['resource_id']})

        hdx_rsc_name = data.get('hdx_rsc_name')
        if hdx_rsc_name:

            for hdx_rsc in dataset.get_resources():

                if hdx_rsc['name'] == hdx_rsc_name:
                    for item in ['name', 'description', 'url', 'format']:
                        hdx_rsc[item] = rsc[item]
                    hdx_rsc.create_in_hdx()
                    hdx_rsc.create_datastore()
                    return hdx_rsc
        else:
            data_dict = {
                'package_id': dataset['id'],
                'name': rsc.get('name'),
                'format': rsc.get('format'),
                'description': rsc.get('description'),
                'url': rsc.get('url'),
            }

            rsc_hdx = Resource(initial_data=data_dict)
            rsc_hdx.check_url_filetoupload()
            rsc_hdx.create_in_hdx()
            rsc_hdx.create_datastore()
            rsc['hdx_name_resource'] = rsc['name']
            try:
                dict_res = {
                    'id': rsc['id'],
                    'hdx_name_resource': rsc['name']
                }
                resource = toolkit.get_action('resource_update')({
                    'ignore_auth': True,
                }, dict_res)
            except ValidationError as e:
                try:
                    raise ValidationError(e.error_dict)
                except (KeyError, IndexError):
                    raise ValidationError(e.error_dict)
            return rsc
    except Exception as e:
        log.debug('Unable to push resource in HDX: %s' % str(e))
        return e


def upsert_dataset_to_hdx(context, data_dict):
    u''' Push data resources that belongs to the dataset on HDX

    :param id: the dataset ID in knowledgehub
    :type id: string
    :param metadata_only: whether to update only metadata of dataset
    :type metadata_only: boolean
    :returns: the dataset created/pushed on HDX or error message
    :rtype: dict
    '''
    check_access('package_create', context)

    id = data_dict.get('id')
    if not id:
        raise ValidationError('Dataset id is missing!')

    metadata_only = data_dict.get('metadata_only', False)

    try:

        # setup_logging()
        data = logic.get_action('package_show')(
            {'ignore_auth': True},
            {'id': id})

        owner_org = config.get(u'ckanext.knowledgehub.hdx.owner_org')
        dataset_source = config.get(u'ckanext.knowledgehub.hdx.dataset_source')
        maintainer = config.get(u'ckanext.knowledgehub.hdx.maintainer')
        dataset_date = unicode(datetime.datetime.utcnow())
        data_dict = {
            'name': data.get('name'),
            'notes': data.get('notes', ''),
            'owner_org': owner_org,
            'title': data.get('title'),
            'private': data.get('private'),
            'dataset_source': dataset_source,
            'maintainer': maintainer,
            'dataset_date': dataset_date,
            'data_update_frequency': -1,
            'license_id': data.get('license_id'),
            'methodology': data.get('license_url'),
            'num_resources': data.get('num_resources'),
            'url': data.get('url')
        }

        hdx_dataset = Dataset.read_from_hdx(data['name'])
        if hdx_dataset is not None:
            data_dict['id'] = hdx_dataset['id']

        dataset = Dataset(initial_data=data_dict)
        dataset.check_required_fields(
            ignore_fields=['groups', 'tags'], allow_no_resources=True)
        dataset.create_in_hdx(ignore_check=False)

        if not metadata_only:
            hdx_resources = list(map(
                lambda r: r.get('name'), dataset.get_resources()
            ))

            resources = data['resources']
            dataset = Dataset.read_from_hdx(data['name'])

            for i in range(0, len(resources)):
                resource = resources[i]
            # for resource in resources:
                data_dict = {
                    'resource_id': resource.get('id'),
                    'dataset_name': dataset.get('name')
                }
                if resource['name'] in hdx_resources:
                    data_dict.update({'hdx_rsc_name': resource['name']})
                resources[i] = upsert_resource_to_hdx(context, data_dict)

            kwh_resources = list(map(
                lambda r: r.get('name'), resources
            ))

            hdx_dataset = Dataset.read_from_hdx(data['name'])

            for hdx_resource in hdx_dataset.get_resources():
                if hdx_resource['name'] not in kwh_resources:
                    hdx_resource.delete_from_hdx()

        hdx_newest_dataset = Dataset.read_from_hdx(data['name'])

        hdx_newest_dataset_dict = {
            'name': hdx_newest_dataset['name'],
            'notes': hdx_newest_dataset['notes'],
            'owner_org': hdx_newest_dataset['owner_org'],
            'title': hdx_newest_dataset['title'],
            'private': hdx_newest_dataset['private'],
            'dataset_source': hdx_newest_dataset['dataset_source'],
            'maintainer': hdx_newest_dataset['maintainer'],
            'dataset_date': hdx_newest_dataset['dataset_date'],
            'data_update_frequency':
                hdx_newest_dataset['data_update_frequency'],
            'license_id': hdx_newest_dataset['license_id'],
            'methodology': hdx_newest_dataset['methodology'],
            'num_resources': hdx_newest_dataset['num_resources'],
            'url': hdx_newest_dataset['url'],
            'package_creator': hdx_newest_dataset['package_creator'],
            'relationships_as_object':
                hdx_newest_dataset['relationships_as_object'],
            'id': hdx_newest_dataset['id'],
            'metadata_created': hdx_newest_dataset['metadata_created'],
            'archived': hdx_newest_dataset['archived'],
            'metadata_modified': hdx_newest_dataset['metadata_modified'],
            'state': hdx_newest_dataset['state'],
            'version': hdx_newest_dataset['version'],
            'type': hdx_newest_dataset['type'],
            'total_res_downloads': hdx_newest_dataset['total_res_downloads'],
            'pageviews_last_14_days':
                hdx_newest_dataset['pageviews_last_14_days'],
            'creator_user_id': hdx_newest_dataset['creator_user_id'],
            'organization': hdx_newest_dataset['organization'],
            'num_tags': hdx_newest_dataset['num_tags'],
            'tags': hdx_newest_dataset['tags'],
            'dataset_preview': hdx_newest_dataset['dataset_preview'],
            'updated_by_script': hdx_newest_dataset['updated_by_script'],
            'is_fresh': hdx_newest_dataset['is_fresh'],
            'solr_additions': hdx_newest_dataset['solr_additions'],
            'relationships_as_subject':
                hdx_newest_dataset['relationships_as_subject'],
            'is_requestdata_type': hdx_newest_dataset['is_requestdata_type'],
        }

        data['hdx_name'] = hdx_newest_dataset_dict['name']
        try:
            toolkit.get_action('package_update')(context, data)
        except ValidationError as e:
            try:
                raise ValidationError(e.error_dict)
            except (KeyError, IndexError):
                raise ValidationError(e.error_dict)

        return hdx_newest_dataset_dict

    except Exception as e:
        log.debug('Unable to push dataset in HDX: %s' % str(e))


def notification_create(context, data_dict):
    '''Creates new notification intended for a particular user (recepient).

    :param title: `str`, the notification title.
    :param description: `str`, _optional_, the notification description.
    :param link: `str`, URL,  optional link for this notification. When
        displayed, the user can click on this notification and will be
        redirected to this url.
    :param image: `str`, optional url of an image to show along with the
        notification.

    :returns: `dict`, the newely created notification object.
    '''
    check_access('notification_create', context)

    data, errors = _df.validate(
        data_dict,
        knowledgehub_schema.notification_create_schema(),
        context
    )

    if errors:
        raise ValidationError(errors)

    recepient = data['recepient']

    try:
        user = toolkit.get_action('user_show')({
            'ignore_auth': True,
        }, {
            'id': recepient,
        })
        recepient = user['id']
    except logic.NotFound:
        raise ValidationError({'recepient': _('No such user')})

    notification = Notification(title=data['title'],
                                description=data.get('description'),
                                recepient=recepient,
                                link=data.get('link'),
                                image=data.get('image'))
    notification.save()
    model.Session.flush()

    return _table_dictize(notification, context)


def post_create(context, data_dict):
    '''Creates a new post to be shown in the news feed.

    :param title: `str`, the post title. Required.
    :param description: `str`, the post description. Optional.
    :param entity_type: `str`, the type of the referenced entity. May be one of
        `dashboard`, `dataset`, `research_question` or `visualization`.
        Optional.
    :param entity_ref: `str`, the ID (reference, like dataset ID or dashboard
        ID) of the refrenced entity in the post. Required if `entity_type`
        is set.

    :returns: `dict`, the newly created post data.
    '''
    entities_actions = {
        'dashboard': 'dashboard_show',
        'dataset': 'package_show',
        'research_question': 'research_question_show',
        'visualization': 'resource_view_show',
    }

    errors = {}
    if 'title' not in data_dict:
        errors['title'] = _('Missing Value')

    entity_type = data_dict.get('entity_type')

    if entity_type:
        if 'entity_ref' not in data_dict:
            errors['entity_ref'] = _('Missing Value')
        if entity_type not in entities_actions:
            errors['entity_type'] = _('Invalid value. '
                                      'Must be one of: %s' % ', '.join(
                                          entities_actions.keys()))

    if errors:
        raise logic.ValidationError(errors)

    check_access('post_create', context, data_dict)

    user = context.get('auth_user_obj')
    if not user:
        raise logic.NotAuthorized()

    entity_ref = None

    if entity_type:
        action = entities_actions[entity_type]

        entity = toolkit.get_action(action)(context, {
            'id': data_dict['entity_ref'],
        })

        entity_ref = entity['id']

    post = Posts(
        title=data_dict['title'],
        description=data_dict.get('description'),
        entity_type=entity_type,
        entity_ref=entity_ref,
        created_by=user.id,
    )

    post.save()
    model.Session.commit()

    post_data = _table_dictize(post, context)

    Posts.add_to_index(post_data)

    return post_data


def request_access(context, data_dict):
    '''Creates a request for access to data (dataset, dashboard or
    visualization).

    The request will be automatically assigned to the organization
    administrators to which the entity belongs to and to the system admins,
    that have access and can grant this request.

    User authentication must be supplied. This action is avaialble for all
    logged in users.

    :param entity_type: `str`, the type of entity: dataset, dashboard or
        visualization.
    :param entity_ref: `str`, the ID (reference) of the entity requested, like
        the ID of the dataset or dashboard.

    :returns: `dict`, dict representation of the request object.
    '''
    check_access('request_access', context, data_dict)
    user = context.get('auth_user_obj')
    if not user:
        raise logic.NotAuthorized(_('Must be logged in to request access.'))

    entity_type = data_dict.get('entity_type', '').lower()
    entity_ref = data_dict.get('entity_ref')
    errors = {}
    if not entity_type:
        errors['entity_type'] = [_('Missing Value')]
    if not entity_ref:
        errors['entity_ref'] = [_('Missing Value')]

    if entity_type not in ['dashboard', 'visualization', 'dataset']:
        errors['entity_type'] = errors.get('entity_type', [])
        errors['entity_type'].append(_('Invalid value'))

    if errors:
        raise ValidationError(errors)

    existing_request = AccessRequest.get_active_for_user_and_entity(
        entity_type,
        entity_ref,
        user.id
    )

    if existing_request:
        raise ValidationError({'id': [_('Request already created.')]})

    entities_actions = {
        'dashboard': 'dashboard_show',
        'dataset': 'package_show',
        'visualization': 'resource_view_show',
    }

    entity = None
    action = entities_actions[entity_type]
    try:
        entity = toolkit.get_action(action)({
            'ignore_auth': True,
        }, {
            'id': entity_ref,
        })
    except logic.NotFound as e:
        raise e
    except Exception as e:
        log.error('Failed to get entity using %s. Error: %s', action, str(e))
        log.exception(e)
        raise e

    # Lookup organization admins and system admins
    organizations = set()
    if entity_type == 'dataset':
        organizations.add(entity.get('owner_org'))
    elif entity_type == 'visualization':
        try:
            dataset = toolkit.get_action('package_show')({
                'ignore_auth': True,
            }, {
                'id': entity['package_id'],
            })
        except logic.NotFound as e:
            raise e
        except Exception as e:
            log.error('Failed to fetch dataset for visualization. '
                      'Dataset: %s. Error: %s', entity['package_id'], str(e))
            log.exception(e)
            raise e
        organizations.add(dataset.get('owner_org'))
    elif entity_type == 'dashboard':
        datasets = entity.get('datasets') or ''
        datasets = datasets.split(',')
        for dataset in datasets:
            dataset = dataset.strip()
            if not dataset:
                continue
            try:
                dataset = toolkit.get_action('package_show')({
                    'ignore_auth': True,
                }, {
                    'id': dataset,
                })
            except logic.NotFound as e:
                raise e
            except Exception as e:
                log.error('Failed to fetch dataset for dashboard. '
                          'Dataset: %s. Error: %s', dataset, str(e))
                log.exception(e)
                raise e

            organizations.add(dataset.get('owner_org'))
    else:
        log.warning('Entity type is %s', entity_type)

    users = set()
    for organization in organizations:
        if not organization:
            continue
        try:
            members = toolkit.get_action('member_list')({
                'ignore_auth': True,
            }, {
                'id': organization,
                'object_type': 'user',
                'capacity': 'admin',
            })
            for member in members:
                users.add(member[0])
        except Exception as e:
            log.warning('Failed to fetch admins for organization %s. '
                        'Error: %s', organization, str(e))
            log.exception(e)

    sysadmins = _find_sysadmins()
    for sysadmin in sysadmins:
        users.add(sysadmin.id)

    try:
        entity_link = None
        if entity_type == 'dataset':
            entity_link = url_for(
                controller='package',
                action='read',
                id=entity.get('name'))
        elif entity_type == 'visualization':
            entity_link = url_for(
                controller='package',
                action='resource_read',
                id=entity.get('package_id'),
                resource_id=entity.get('resource_id'),
                view_id=entity.get('id'))
        elif entity_type == 'dashboard':
            entity_link = url_for(
                'dashboards.view',
                name=entity.get('name'))

        model.Session.begin(subtransactions=True)
        access_request = AccessRequest(
            user_id=user.id,
            entity_type=entity_type,
            entity_ref=entity_ref,
            entity_title=entity.get('title'),
            entity_link=entity_link,
        )

        access_request.save()

        for user_id in users:
            assigned = AssignedAccessRequest(
                request_id=access_request.id,
                user_id=user_id,
            )
            assigned.save()

        model.Session.commit()
        model.Session.flush()
    except Exception as e:
        log.exception(e)
        model.Session.rollback()
        raise e

    access_request_dict = _table_dictize(access_request, context)

    if user.id in users:
        users.remove(user.id)

    for recipient in users:
        # Send notification to approvers
        try:
            toolkit.get_action('notification_create')({
                'ignore_auth': True,
                'auth_user_obj': user,
            }, {
                'title': _('Request for access'),
                'description': _('Access was requested to {}.').format(
                    access_request.entity_title),
                'link': url_for('user_dashboard.requests_list'),
                'recepient': recipient,
            })
        except Exception as e:
            log.error('Failed to send notification for access request '
                      'to user %s. Error: %s',
                      recipient,
                      str(e))
            log.exception(e)

        # Send notification email to approver
        try:
            schedule_notification_email(recipient, 'access_request', {
                'entity_type': access_request.entity_type,
                'entity_title': access_request.entity_title,
                'entity_link': access_request.entity_link,
                'requested_by': user,
            })
        except Exception as e:
            log.error('Failed to schedule notification email to %s. Error: %s',
                      recipient, str(e))
            log.exception(e)

    return access_request_dict


def _find_sysadmins():
    '''Locates the system admins of the portal.
    '''
    q = model.Session.query(model.User)
    q = q.filter(model.user_table.c.sysadmin == True)
    q = q.filter(model.user_table.c.state == 'active')
    sysadmins = []
    for user in q.all():
        sysadmins.append(user)
    return sysadmins


def comment_create(context, data_dict):
    '''Creates a comment.

    The comment can be directly to an entity (ref), or can be a reply to other
    comment.

    :param ref: `str`, reference to the entity being commented on (post,
        dataset, research question etc)
    :param content: `str`, the comment content.
    :param reply_to: `str`, optional, if provided, then this comment is a reply
        to another comment with the ID given in this parameter.

    :returns: `dict`, dictized representation of the comment.
    '''
    check_access('comment_create', context, data_dict)

    user = context.get('auth_user_obj')

    ref = data_dict.get('ref', '').strip()
    content = data_dict.get('content', '').strip()
    reply_to = data_dict.get('reply_to')
    if reply_to:
        reply_to = reply_to.strip()

    errors = {}

    if not ref:
        errors['ref'] = [_('Missing value')]
    if not content:
        errors['content'] = [_('Missing value')]

    if errors:
        raise ValidationError(errors)

    try:
        model.Session.begin(subtransactions=True)
        comment = Comment(
            ref=ref,
            content=content,
            reply_to=reply_to,
            created_by=user.id,
        )

        if reply_to:
            parent = Comment.get(reply_to)
            if not parent:
                raise NotFound('Reply to comment not found')
            if parent.thread_id is None:
                comment.thread_id = parent.id
            else:
                comment.thread_id = parent.thread_id

        comment.save()

        Comment.increment_comment_count(comment)

        model.Session.commit()
    except Exception as e:
        log.error('Failed to created comment. Error: %s', str(e))
        log.exception(e)
        model.Session.rollback()
        raise e

    comment = _table_dictize(comment, context)

    comment['user'] = {
        'id': user.id,
        'name': user.name,
        'display_name': user.display_name or user.name,
        'email_hash': user.email_hash,
    }
    comment['human_timestamp'] = plugin_helpers.human_elapsed_time(
        comment['created_at'])
    comment['display_content'] = render_markdown(comment.get('content') or '')

    return comment
