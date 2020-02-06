import logging
import datetime
import os
import subprocess

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
from ckan.logic.action.create import (
    package_create as ckan_package_create,
)
from ckan.lib.helpers import url_for

from ckanext.knowledgehub.logic import schema as knowledgehub_schema
from ckanext.knowledgehub.logic.action.get import user_query_show
from ckanext.knowledgehub.model.theme import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.model import Dashboard
from ckanext.knowledgehub.model import ResourceFeedbacks
from ckanext.knowledgehub.model import ResourceValidate
from ckanext.knowledgehub.model import ResourceValidation
from ckanext.knowledgehub.model import KWHData
from ckanext.knowledgehub.model import RNNCorpus
from ckanext.knowledgehub.model import Visualization
from ckanext.knowledgehub.model import UserIntents
from ckanext.knowledgehub.model import UserQuery
from ckanext.knowledgehub.model import UserQueryResult
from ckanext.knowledgehub.backend.factory import get_backend
from ckanext.knowledgehub.lib.writer import WriterService
from ckanext.knowledgehub import helpers as plugin_helpers

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

    research_question.save()

    research_question_data = _table_dictize(research_question, context)
    # Add to index
    try:
        ResearchQuestion.add_to_index(research_question_data)
    except Exception as e:
        ResearchQuestion.delete(research_question.id)
        raise e

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

    return ckan_rsc_create(context, data_dict)


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

    dashboard_data = _table_dictize(dashboard, context)

    # Add to index
    Dashboard.add_to_index(dashboard_data)

    return dashboard_data


def package_create(context, data_dict):
    return ckan_package_create(context, data_dict)


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

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.resource_validation_schema(),
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
            requested_at=requested_at
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


def kwh_data_create(context, data_dict):
    '''
    Store Knowledge Hub data
        :param type
        :param content
    '''
    check_access('kwh_data', context, data_dict)

    session = context['session']

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.kwh_data_schema(),
                                context)

    if errors:
        raise ValidationError(errors)

    user = context.get('user')
    user_data = model.User.by_name(user.decode('utf8'))
    if user_data:
        data['user'] = user_data.id

    kwh_data = KWHData.get(
        user=data.get('user'),
        content=data.get('content'),
        type=data.get('type')
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
    return model_dictize.tag_dictize(tag, context)
