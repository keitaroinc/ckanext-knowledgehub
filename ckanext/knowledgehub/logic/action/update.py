import logging
import datetime
import re

from sqlalchemy import exc
from psycopg2 import errorcodes as pg_errorcodes
from werkzeug.datastructures import FileStorage as FlaskFileStorage

from ckan.logic import chained_action
from ckanext.datastore.backend import DatastoreBackend
import ckanext.datastore.logic.schema as dsschema
from ckanext.datastore.logic.action import set_datastore_active_flag

from hdx.data.dataset import Dataset

import ckan.lib.navl.dictization_functions
from ckan.common import _, config
import ckanext.datastore.helpers as datastore_helpers

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
from ckanext.knowledgehub.model import ResourceValidate
from ckanext.knowledgehub.model import ResourceValidation
from ckanext.knowledgehub.model import Dashboard
from ckanext.knowledgehub.model import KWHData
from ckanext.knowledgehub.model import Visualization
from ckanext.knowledgehub.model import UserIntents, DataQualityMetrics
from ckanext.knowledgehub.model import Keyword
from ckanext.knowledgehub.model import UserProfile
from ckanext.knowledgehub.model.keyword import ExtendedTag
from ckanext.knowledgehub.model import Notification
from ckanext.knowledgehub.backend.factory import get_backend
from ckanext.knowledgehub.lib.writer import WriterService
from ckanext.knowledgehub import helpers as plugin_helpers
from ckanext.knowledgehub.logic.jobs import schedule_data_quality_check
from ckanext.knowledgehub.lib.profile import user_profile_service

from sqlalchemy.orm.attributes import flag_modified


log = logging.getLogger(__name__)

_df = lib.navl.dictization_functions
_table_dictize = lib.dictization.table_dictize
_get_or_bust = logic.get_or_bust
_validate = ckan.lib.navl.dictization_functions.validate


check_access = toolkit.check_access
NotFound = logic.NotFound
ValidationError = toolkit.ValidationError
NotAuthorized = toolkit.NotAuthorized


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
    context['title'] = theme.title
    context['description'] = theme.description
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

    theme_data = _table_dictize(theme, context)

    # Update kwh data
    try:
        data_dict = {
            'type': 'theme',
            'entity_id': theme_data.get('id'),
            'title': theme_data.get('title'),
            'description': theme_data.get('description')
        }
        logic.get_action(u'kwh_data_update')(context, data_dict)
    except Exception as e:
        log.debug('Unable to update theme {} in knowledgehub data: {}'.format(
            theme_data.get('id'), str(e)
        ))

    return theme_data


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
    context['title'] = sub_theme.title
    context['description'] = sub_theme.description
    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.sub_theme_update(),
                                context)

    if errors:
        raise logic.ValidationError(errors)

    user = context.get('user')
    data_dict['modified_by'] = model.User.by_name(user.decode('utf8')).id

    filter = {'id': id}
    st = SubThemes.update(filter, data_dict)

    sub_theme_data = st.as_dict()

    # Update kwh data
    try:
        data_dict = {
            'type': 'sub_theme',
            'entity_id': sub_theme_data.get('id'),
            'title': sub_theme_data.get('title'),
            'description': sub_theme_data.get('description')
        }
        logic.get_action(u'kwh_data_update')(context, data_dict)
    except Exception as e:
        log.debug(
            'Unable to update sub-theme {} in knowledgehub data: {}'.format(
                sub_theme_data.get('id'),
                str(e))
        )

    return sub_theme_data


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
    if not data_dict.get('tags'):
        data['tags'] = None

    if errors:
        raise logic.ValidationError(errors)

    user = context.get('user')

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

    data['modified_by'] = model.User.by_name(user.decode('utf8')).id

    filter = {'id': id}
    data.pop('__extras', None)
    rq = ResearchQuestion.update(filter, data)
    rq_data = rq.as_dict()

    # Update index
    ResearchQuestion.update_index_doc(rq_data)

    # Update kwh data
    try:
        data_dict = {
            'type': 'research_question',
            'entity_id': rq_data.get('id'),
            'title': rq_data.get('title')
        }
        logic.get_action(u'kwh_data_update')(context, data_dict)
    except Exception as e:
        log.debug(
            'Unable to update sub-theme {} in knowledgehub data: {}'.format(
                    rq_data.get('id'),
                    str(e))
        )

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

            filename = data_dict.get('url')
            if not filename:
                filename = '{}_{}.{}'.format(
                    data_dict.get('db_type'),
                    str(datetime.datetime.utcnow()),
                    'csv'
                )

            data_dict['upload'] = FlaskFileStorage(stream, filename)

    result = ckan_rsc_update(context, data_dict)
    schedule_data_quality_check(result['package_id'])

    return result


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

    if not data_dict.get('tags'):
        data['tags'] = None

    context['resource_view'] = resource_view
    context['resource'] = model.Resource.get(resource_view.resource_id)
    # TODO need to implement custom authorization actions
    # check_access('resource_view_update', context, data_dict)

    old_resource_view_data = model_dictize.resource_view_dictize(resource_view,
                                                                 context)

    # before update

    resource_view = model_save.resource_view_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit()
    resource_view_data = model_dictize.resource_view_dictize(resource_view,
                                                             context)

    # Update index
    Visualization.update_index_doc(resource_view_data)

    # Update kwh data
    try:
        data_dict = {
            'type': 'visualization',
            'entity_id': resource_view_data.get('id'),
            'title': resource_view_data.get('title'),
            'description': resource_view_data.get('description')
        }
        logic.get_action(u'kwh_data_update')(context, data_dict)
    except Exception as e:
        log.debug(
            'Unable to update visualization %s in knowledgehub data: %s' %
            (resource_view_data.get('id'), str(e))
        )

    # this check is done for the unit tests
    if resource_view_data.get('__extras'):
        ext = resource_view_data['__extras']
        ext_old = old_resource_view_data['__extras']
        if ext_old.get('research_questions') or ext.get('research_questions'):
            plugin_helpers.update_rqs_in_dataset(
                old_resource_view_data, resource_view_data)

    return resource_view_data


def dashboard_update(context, data_dict):
    '''
    Updates existing dashboard

        :param id
        :param name
        :param description
        :param title
        :param indicators
        :param tags
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

    datasets = data_dict.get('datasets')
    if datasets is not None:
        if isinstance(datasets, unicode):
            dashboard.datasets = datasets
        elif isinstance(datasets, list):
            dashboard.datasets = ', '.join(datasets)
    else:
        dashboard.datasets = ''

    items = ['name', 'title', 'description',
             'indicators', 'source', 'type', 'tags']

    for item in items:
        setattr(dashboard, item, data.get(item))

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

    dashboard_type = data.get('type')
    if dashboard_type != 'external':
        dashboard.source = ''
        dashboard.datasets = ''

    dashboard.modified_at = datetime.datetime.utcnow()
    dashboard.save()

    session.add(dashboard)
    session.commit()

    dashboard_data = _table_dictize(dashboard, context)

    # Update index
    Dashboard.update_index_doc(dashboard_data)

    # Update kwh data
    try:
        data_dict = {
            'type': 'dashboard',
            'entity_id': dashboard_data.get('id'),
            'title': dashboard_data.get('title'),
            'description': dashboard_data.get('description')
        }
        logic.get_action(u'kwh_data_update')(context, data_dict)
    except Exception as e:
        log.debug(
            'Unable to update dashboard %s in knowledgehub data: %s'
            % (dashboard_data.get('id'), str(e))
        )

    return dashboard_data


def package_update(context, data_dict):
    u'''Wraps the CKAN's core 'package_update' function to schedule a check for
    Data Quality metrics calculation when the package has been updated.
    '''

    package_old_info = toolkit.get_action('package_show')(context, {
        'id': data_dict.get('id')
    })
    print("<In package update>")
    try:
        hdx_dataset = Dataset.read_from_hdx(package_old_info.get('name'))
    except Exception as e:
        print("HDX error: {}".format(str(e)))

    result = ckan_package_update(context, data_dict)
    schedule_data_quality_check(result['id'])

    if hdx_dataset:
        upsert_dataset_to_hdx = {
            'id': package_old_info.get('id'),
            'metadata_only': False
        }
        logic.get_action('upsert_dataset_to_hdx')(
            context,
            upsert_dataset_to_hdx
        )
    try:
        data_dict = {
            'type': 'dataset',
            'entity_id': result.get('id'),
            'title': result.get('title'),
            'description': result.get('notes')
        }
        logic.get_action(u'kwh_data_update')(context, data_dict)
    except Exception as e:
        log.debug(
            'Unable to update dataset {} to knowledgehub data: {}'.format(
                result.get('id'), str(e)
            ))

    return result


def kwh_data_update(context, data_dict):
    ''' Update existing knowledgehub data or create new one

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
    :param title: the title of the entity
    :type title: string
    :param description: the description of the entity (optional)
    :type description: string
    :param entity_id: the ID of the entity
    :type entity_id: string
    :returns: the updated data
    :rtype: dict
    '''
    check_access('kwh_data', context, data_dict)

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.kwh_data_schema_update(),
                                context)

    if errors:
        raise ValidationError(errors)

    user = context.get('user')
    if user:
        data['user'] = model.User.by_name(user.decode('utf8')).id

    data_filter = {data['type']: data['entity_id']}
    kwh_data = KWHData.get(**data_filter).first()

    if kwh_data:
        update_data = _table_dictize(kwh_data, context)
        update_data.pop('id')
        update_data.pop('created_at')
        update_data['title'] = data.get('title')
        update_data['description'] = data.get('description')

        kwh_data = KWHData.update(data_filter, update_data)
    else:
        data_dict = {
            'user': data.get('user'),
            'type': data.get('type'),
            'title': data.get('title'),
            'description': data.get('description'),
            data['type']: data['entity_id']
        }
        kwh_data = KWHData(**data_dict)
        kwh_data.save()

    return kwh_data.as_dict()


def user_intent_update(context, data_dict):
    ''' Updates an existing user intent

    :param id: the ID of the user intent
    :type name: string

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

    :returns: the updated user intent
    :rtype: dictionary
    '''

    try:
        check_access('user_intent_update', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system '
                              u'administrator to administer'))

    id = data_dict.get("id")
    if not id:
        raise ValidationError({'id': _('Missing value')})

    intent = UserIntents.get(id)
    if not intent:
        raise NotFound(_('Intent was not found.'))

    items = [
        'primary_category',
        'theme',
        'sub_theme',
        'research_question',
        'inferred_transactional',
        'inferred_navigational',
        'inferred_informational',
        'curated',
        'accurate'
    ]

    for item in items:
        if data_dict.get(item):
            setattr(intent, item, data_dict.get(item))

    session = context['session']

    intent.save()
    session.add(intent)
    session.commit()

    return _table_dictize(intent, context)


_dq_validators = {
    'completeness': {
        'total': int,
        'complete': int,
        'value': float,
    },
    'timeliness': {
        'records': int,
        'average': int,
        'total': int,
        'value': str,
    },
    'validity': {
        'valid': int,
        'total': int,
        'value': float,
    },
    'uniqueness': {
        'unique': int,
        'total': int,
        'value': float,
    },
    'consistency': {
        'consistent': int,
        'total': int,
        'value': int,
    },
    'accuracy': {
        'accurate': int,
        'inaccurate': int,
        'total': int,
        'value': float,
    }
}


def _patch_data_quality(context, data_dict, _type):
    if not data_dict.get('id'):
        raise ValidationError({'id': _(u'Missing Value')})
    action = 'package_show' if _type == 'package' else 'resource_show'
    try:
        check_access(action, context, data_dict)
    except NotAuthorized as e:
        raise NotAuthorized(_(str(e)))

    # validate input
    dimensions = ['completeness', 'uniqueness', 'timeliness', 'validity',
                  'accuracy', 'consistency']
    for dimension in dimensions:
        values = data_dict.get(dimension)
        if values:
            validators = _dq_validators[dimension]
            for field, _ftype in validators.items():
                value = values.get(field)
                if _type == 'package' and field != 'value':
                    continue
                if value is None:
                    raise ValidationError({field: _('Missing Value')})
                if isinstance(value, str) or isinstance(value, unicode):
                    try:
                        _ftype(value)
                    except Exception as e:
                        raise ValidationError({
                            field: _('Invalid Value' +
                                     "(%s) '%s'" % (dimension, value))
                        })
                else:
                    try:
                        values[field] = _ftype(value)
                    except Exception:
                        raise ValidationError({field: _('Invalid Value Type')})
    db_metric = DataQualityMetrics.get(_type, data_dict['id'])
    if not db_metric:
        db_metric = DataQualityMetrics(type=_type, ref_id=data_dict['id'])

    db_metric.metrics = db_metric.metrics or {}

    for field, values in data_dict.items():
        if field not in dimensions:
            continue
        setattr(db_metric, field, values['value'])  # set the main metric
        db_metric.metrics[field] = values
        db_metric.metrics[field]['manual'] = values.get('manual', True)

    db_metric.modified_at = datetime.datetime.now()
    db_metric.save()

    results = {}
    for dimension in dimensions:
        results[dimension] = getattr(db_metric, dimension)

    results['calculated_on'] = db_metric.modified_at.isoformat()
    results['details'] = db_metric.metrics

    return results


def package_data_quality_update(context, data_dict):
    return _patch_data_quality(context, data_dict, 'package')


def resource_data_quality_update(context, data_dict):
    return _patch_data_quality(context, data_dict, 'resource')


@toolkit.side_effect_free
def resource_validate_update(context, data_dict):
    ''' Updates an existing validation status of resource

    :param what: validation status of the resource
    :type name: string

    :returns: the updated validation status
    :rtype: dictionary
    '''

    try:
        logic.check_access('resource_validate_update', context, data_dict)
    except logic.NotAuthorized:
        raise logic.NotAuthorized(_(u'Need to be system '
                                    u'administrator to administer'))

    status = data_dict['what']
    user = context['auth_user_obj']

    name = getattr(user, "fullname")
    if not name:
        name = context['user']

    when = datetime.datetime.utcnow().strftime(
        '%Y-%m-%dT%H:%M:%S'
    )
    id = logic.get_or_bust(data_dict, 'id')
    data_dict.pop('id')

    resource_validate = ResourceValidate.get(resource=id)

    if not resource_validate:
        log.debug('Could not find validation report %s', id)
        raise logic.NotFound(_('Validation report was not found.'))

    filter = {'resource': id}
    rvu = {
        'what': status,
        'when': when,
        'who': name
    }
    st = ResourceValidate.update(filter, rvu)

    return st.as_dict()


def resource_validation_update(context, data_dict):
    '''
    Update resource validation asignee

    :param dataset
    :param resource
    :param user
    :param admin
    :param admin_email
    '''
    check_access('resource_validation_update', context, data_dict)

    resource_schema = knowledgehub_schema.resource_validation_schema()
    data, errors = _df.validate(data_dict,
                                resource_schema,
                                context)

    if errors:
        raise ValidationError(errors)

    if data.get('admin'):
        usr = context.get('user')

        dataset = data_dict.get('package_id')
        resource = data_dict.get('id')
        user = model.User.by_name(usr.decode('utf8')).id
        admin = data_dict.get('admin')
        admin_email = model.User.by_name(admin).email
        requested_at = datetime.datetime.utcnow()

        rv = ResourceValidation.get(
            dataset=dataset,
            resource=resource
        ).first()

        if not rv:
            raise NotFound
        else:
            filter = {'id': rv.id}
            rvu = {
                'user': user,
                'admin': admin,
                'admin_email': admin_email,
                'requested_at': requested_at
            }
            rv.update(filter, rvu)

            return _table_dictize(rv, context)


def resource_validation_status(context, data_dict):
    '''
    Update resource validation status

    :param dataset
    :param resource
    :param user
    :param admin
    :param admin_email
    '''
    check_access('resource_validation_status', context, data_dict)

    rc_validation_schema = knowledgehub_schema.resource_validation_schema()
    data, errors = _df.validate(data_dict,
                                rc_validation_schema,
                                context)

    if errors:
        raise ValidationError(errors)

    usr = context.get('user')

    resource = data_dict.get('resource')
    admin = model.User.by_name(usr.decode('utf8')).name
    status = 'validated'
    validated_at = datetime.datetime.utcnow()

    vr = ResourceValidation.get(
        resource=resource,
        admin=admin
    ).first()

    if not vr:
        raise NotFound
    else:
        filter = {'id': vr.id}
        vru = {
            'status': status,
            'validated_at': validated_at
        }
        vr.update(filter, vru)

        return _table_dictize(vr, context)


def resource_validation_revert(context, data_dict):
    '''
    Revert resource validation status

    :param dataset
    :param resource
    :param user
    :param admin
    :param admin_email
    '''
    check_access('resource_validation_revert', context, data_dict)

    rc_validation_schema = knowledgehub_schema.resource_validation_schema()
    data, errors = _df.validate(data_dict,
                                rc_validation_schema,
                                context)

    if errors:
        raise ValidationError(errors)

    usr = context.get('user')

    resource = data_dict.get('resource')
    admin = model.User.by_name(usr.decode('utf8')).name
    status = 'not_validated'
    validated_at = None

    vr = ResourceValidation.get(
        resource=resource,
        admin=admin
    ).first()

    if not vr:
        raise NotFound
    else:
        filter = {'id': vr.id}
        vru = {
            'status': status,
            'validated_at': validated_at
        }
        vr.update(filter, vru)

        return _table_dictize(vr, context)


def tag_update(context, data_dict):
    ''' Update the tag name or vocabulary

    :param id: id or name of the tag
    :type id: string
    :param name: the name of the tag
    :type name: string
    :param vocabulary_id: the id of the vocabulary (optional)
    :type vocabulary_id: string

    :returns: the updated tag
    :rtype: dictionary
    '''

    model = context['model']

    try:
        check_access('tag_create', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system '
                              u'administrator to administer'))

    schema = knowledgehub_schema.tag_update_schema()
    data, errors = _df.validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    tag = ExtendedTag.get_with_keyword(data.get('id'))
    if not tag:
        raise NotFound(_('Tag was not found'))

    tag.name = data_dict.get('name', tag.name)

    # Force the vocabulary id update always.
    tag.keyword_id = data_dict.get('keyword_id')

    session = context['session']
    tag.save()
    session.commit()

    return _table_dictize(tag, context)


def keyword_update(context, data_dict):
    '''Updates the tags for a keyword.

    :param id: `str`, the id or the name of the keyword to update.
    :param tags: `list` of `str`, the tags that this keyword should contain. If
        the tag does not exist, it will be created and added to this keyword.
        The tags that were removed from this keyword will be set as free tags
        and will not be removed.

    :returns: `dict`, the updated keyword.
    '''
    check_access('keyword_update', context)
    if 'id' not in data_dict:
        raise ValidationError({'id': _('Missing Value')})
    existing = Keyword.get(data_dict['id'])
    if not existing:
        existing = Keyword.by_name(data_dict['id'])
    if not existing:
        raise logic.NotFound(_('Not found'))

    if data_dict.get('name', '').strip():
        keyword_name = re.sub(r'\s+', '-', data_dict['name'].strip())
        existing.name = keyword_name

    existing.modified_at = datetime.datetime.utcnow()
    existing.save()

    for tag in Keyword.get_tags(existing.id):
        tag.keyword_id = None
        tag.save()

    kwd_dict = _table_dictize(existing, context)
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
        db_tag.keyword_id = existing.id
        db_tag.save()
        tag_dict = _table_dictize(db_tag, context)
        kwd_dict['tags'].append(tag_dict)

    return kwd_dict


@chained_action
def datastore_create(action, context, data_dict):
    '''Adds a new table to the DataStore.

    The datastore_create action allows you to post JSON data to be
    stored against a resource. This endpoint also supports altering tables,
    aliases and indexes and bulk insertion. This endpoint can be called
    multiple times to initially insert more data, add fields, change the
    aliases or indexes as well as the primary keys.

    To create an empty datastore resource and a CKAN resource at the same time,
    provide ``resource`` with a valid ``package_id`` and omit the
    ``resource_id``.

    If you want to create a datastore resource from the content of a file,
    provide ``resource`` with a valid ``url``.

    See :ref:`fields` and :ref:`records` for details on how to lay out records.

    :param resource_id: resource id that the data is going to be stored
                        against.
    :type resource_id: string
    :param force: set to True to edit a read-only resource
    :type force: bool (optional, default: False)
    :param resource: resource dictionary that is passed to
        :meth:`~ckan.logic.action.create.resource_create`.
        Use instead of ``resource_id`` (optional)
    :type resource: dictionary
    :param aliases: names for read only aliases of the resource. (optional)
    :type aliases: list or comma separated string
    :param fields: fields/columns and their extra metadata. (optional)
    :type fields: list of dictionaries
    :param records: the data, eg: [{"dob": "2005", "some_stuff": ["a", "b"]}]
                    (optional)
    :type records: list of dictionaries
    :param primary_key: fields that represent a unique key (optional)
    :type primary_key: list or comma separated string
    :param indexes: indexes on table (optional)
    :type indexes: list or comma separated string
    :param triggers: trigger functions to apply to this table on update/insert.
        functions may be created with
        :meth:`~ckanext.datastore.logic.action.datastore_function_create`.
        eg: [
        {"function": "trigger_clean_reference"},
        {"function": "trigger_check_codes"}]
    :type triggers: list of dictionaries

    Please note that setting the ``aliases``, ``indexes`` or ``primary_key``
    replaces the exising aliases or constraints. Setting ``records`` appends
    the provided records to the resource.

    **Results:**

    :returns: The newly created data object, excluding ``records`` passed.
    :rtype: dictionary

    See :ref:`fields` and :ref:`records` for details on how to lay out records.

    '''
    backend = DatastoreBackend.get_active_backend()
    schema = context.get('schema', dsschema.datastore_create_schema())
    records = data_dict.pop('records', None)
    resource = data_dict.pop('resource', None)
    data_dict, errors = _validate(data_dict, schema, context)
    resource_dict = None
    if records:
        data_dict['records'] = records
    if resource:
        data_dict['resource'] = resource
    if errors:
        raise toolkit.ValidationError(errors)

    toolkit.check_access('datastore_create', context, data_dict)

    if 'resource' in data_dict and 'resource_id' in data_dict:
        raise toolkit.ValidationError({
            'resource': ['resource cannot be used with resource_id']
        })

    if 'resource' not in data_dict and 'resource_id' not in data_dict:
        raise toolkit.ValidationError({
            'resource_id': ['resource_id or resource required']
        })

    if 'resource' in data_dict:
        has_url = 'url' in data_dict['resource']
        # A datastore only resource does not have a url in the db
        data_dict['resource'].setdefault('url', '_datastore_only_resource')
        resource_dict = toolkit.get_action('resource_create')(
            context, data_dict['resource'])
        data_dict['resource_id'] = resource_dict['id']

        # create resource from file
        if has_url:
            if not p.plugin_loaded('datapusher'):
                raise toolkit.ValidationError({'resource': [
                    'The datapusher has to be enabled.']})
            toolkit.get_action('datapusher_submit')(context, {
                'resource_id': resource_dict['id'],
                'set_url_type': True
            })
            # since we'll overwrite the datastore resource anyway, we
            # don't need to create it here
            return

        # create empty resource
        else:
            # no need to set the full url because it will be set in before_show
            resource_dict['url_type'] = 'datastore'
            p.toolkit.get_action('resource_update')(context, resource_dict)
    else:
        if not data_dict.pop('force', False):
            resource_id = data_dict['resource_id']
            _check_read_only(context, resource_id)

    # validate aliases
    aliases = datastore_helpers.get_list(data_dict.get('aliases', []))
    for alias in aliases:
        if not datastore_helpers.is_valid_table_name(alias):
            raise toolkit.ValidationError({
                'alias': [u'"{0}" is not a valid alias name'.format(alias)]
            })
    try:
        result = backend.create(context, data_dict)
    except Exception as e:
        raise toolkit.ValidationError(str(e))
    except InvalidDataError as err:
        raise toolkit.ValidationError(text_type(err))
    # Set the datastore_active flag on the resource if necessary
    model = _get_or_bust(context, 'model')
    resobj = model.Resource.get(data_dict['resource_id'])
    if resobj.extras.get('datastore_active') is not True:
        log.debug(
            'Setting datastore_active=True on resource {0}'.format(resobj.id)
        )
        set_datastore_active_flag(model, data_dict, True)

    result.pop('id', None)
    result.pop('connection_url', None)
    result.pop('records', None)
    return result


def update_tag_in_rq(context, data_dict):
    '''
    Updates the tags for a research question.

    :param id: `str`, the id of the research question to update.
    :param name: `str`, the name of the research question to update.
    :param tag_new: `str`, the new tag of the research question.
    :param tag_old: `str`, the old tag of the research question.

    :returns: the updated research question.
    :rtype: dictionary
    '''

    id = data_dict.get("id")
    if not id:
        raise ValidationError({'id': _('Missing value')})
    id_or_name = data_dict.get('id') or data_dict.get('name')
    new_tag = data_dict.get('tag_new')

    research_question = ResearchQuestion.get(id_or_name=id_or_name).first()
    if not research_question:
        log.debug('Could not find research question %s', id)

    rq_dict = research_question.as_dict()

    tag_list = rq_dict.get('tags').split(',')
    for tag in tag_list:
        if tag == data_dict.get('tag_old'):
            tag_list.remove(tag)
            tag_list.append(new_tag)
    str1 = ","
    tags = str1.join(tag_list)

    result = toolkit.get_action('research_question_update')(context, {
                'id': rq_dict.get('id'),
                'name': rq_dict.get('name'),
                'title': rq_dict.get('title'),
                'tags': tags
                })

    return result


def update_tag_in_dash(context, data_dict):
    '''
    Updates the tags for a dashboard.

    :param id: `str`, the id of the dashboard to update.
    :param name: `str`, the name of the dashboard to update.
    :param tag_new: `str`, the new tag of the dashboard.
    :param tag_old: `str`, the old tag of the dashboard.

    :returns: the updated dashboard.
    :rtype: dictionary
    '''

    id = data_dict.get("id")
    new_tag = data_dict.get('tag_new')
    if not id:
        raise ValidationError({'id': _('Missing value')})
    name_or_id = data_dict.get("id") or data_dict.get("name")

    if name_or_id is None:
        raise ValidationError({'id': _('Missing value')})

    dash = Dashboard.get(name_or_id)
    if not dash:
        log.debug('Could not find dashboard %s', id)
    dash_dict = dash.as_dict()

    tag_list = dash_dict.get('tags').split(',')
    for tag in tag_list:
        if tag == data_dict.get('tag_old'):
            tag_list.remove(tag)
            tag_list.append(new_tag)
    str1 = ","
    tags = str1.join(tag_list)

    result = toolkit.get_action('dashboard_update')(context, {
                'id': dash_dict.get('id'),
                'name': dash_dict.get('name'),
                'title': dash_dict.get('title'),
                'description': dash_dict.get('description'),
                'type': dash_dict.get('type'),
                'source': dash_dict.get('source'),
                'indicators': dash_dict.get('indicators'),
                'created_by': dash_dict.get('created_by'),
                'tags': tags
                })

    return result


def update_tag_in_resource_view(context, data_dict):
    '''
    Updates the tags for a resource view.

    :param id: `str`, the id of the resource view to update.
    :param name: `str`, the name of the resource view to update.
    :param tag_new: `str`, the new tag of the resource view.
    :param tag_old: `str`, the old tag of the resource view.

    :returns: the updated resource view.
    :rtype: dictionary
    '''

    new_tag = data_dict.get('new_tag')
    old_tag = data_dict.get('old_tag')
    id = data_dict.get("id")
    if not id:
        raise ValidationError({'id': _('Missing value')})

    visual = model.Session.query(model.ResourceView).filter_by(id=id)
    if not visual:
        log.debug('Could not find visualization %s', id)
    visual_element = visual.order_by(model.ResourceView.order).all()[0]

    visual_dict = {
        'id': visual_element.id,
        'resource_id': visual_element.resource_id,
        'title': visual_element.title,
        'description': visual_element.description,
        'view_type': visual_element.view_type,
        'order': visual_element.order,
        'config': visual_element.config,
        'tags': visual_element.tags
    }

    if visual_dict.get('tags'):
        tag_list = visual_dict.get('tags').split(',')
        for tag in tag_list:
            if tag == old_tag:
                tag_list.remove(tag)
                tag_list.append(new_tag)
                str1 = ","
                tags = str1.join(tag_list)
                visual_element.tags = tags
                visual_element.save()
                visual_element.commit()
                toolkit.get_action('tag_create')(context, {
                    'name': new_tag,
                })

                return visual_element


def update_tag_in_dataset(context, data_dict):
    '''
    Updates the tags for a dataset.

    :param id: `str`, the id of the dataset to update.
    :param tag_new: `str`, the new tag of the dataset.
    :param tag_old: `str`, the old tag of the dataset.

    :returns: the updated dataset.
    :rtype: dictionary
    '''
    new_tag = data_dict.get('new_tag')
    old_tag = data_dict.get('old_tag')
    id = data_dict.get("id")
    if not id:
        raise ValidationError({'id': _('Missing value')})

    toolkit.get_action('tag_create')(context, {
                    'name': new_tag,
                })

    new_tag_info = model.Tag.by_name(name=new_tag)
    new_tag_dict = {
        u'vocabulary_id': new_tag_info.vocabulary_id,
        u'display_name': new_tag_info.name,
        u'name': new_tag_info.name,
        u'state': u'active',
        u'keyword_id': '',
        u'id': new_tag_info.id
    }

    dataset_info = toolkit.get_action('package_show')(context, {
        'id': id
    })
    dataset_info['tags'].append(new_tag_dict)
    updated_dataset = toolkit.get_action('package_update')(
        context,
        dataset_info
    )

    return updated_dataset


def user_profile_update(context, data_dict):
    u'''Updates the user profile data.

    For regular users, this action updates the user profile data for the
    currently authenticated user.

    For a sysadmin user, an additional parameter (user_id) can be set to update
    the profile data for another user.

    :param user_id: `str`, the id of the user to update the user profile data.
        This parameter is available for sysadmins only, otherwise it will be
        ignored.
    :param user_notified: `bool`, set the flag for user flash notification.
    :param research_questions: `list`, list of research questions IDs to set as
        interests.
    :param keywords: `list`, list of research questions IDs to set as
        interests.
    :param tags: `list`, list of research questions IDs to set as
        interests.
    '''
    check_access('user_profile_update', context, data_dict)
    user = context.get('auth_user_obj')
    user_id = user.id

    if getattr(user, 'sysadmin', False) and data_dict.get('user_id'):
        user_id = data_dict['user_id']

    profile = UserProfile.by_user_id(user_id)
    if not profile:
        profile = UserProfile(user_id=user_id, user_notified=True)
        profile.interests = {}

    interests = data_dict.get('interests', {})
    for interest_type in ['research_questions', 'keywords']:
        if interests.get(interest_type) is not None:
            profile.interests[interest_type] = interests[interest_type]

    if interests.get('tags') is not None:
        profile.interests['tags'] = []
        for tag in interests.get('tags', []):
            try:
                tag = toolkit.get_action('tag_show')({
                    'ignore_auth': True,
                }, {
                    'id': tag,
                })
                profile.interests['tags'].append(tag['name'])
            except Exception as e:
                log.warning('Failed to load tag %s. Error: %s', tag, str(e))

    if profile.interests:
        flag_modified(profile, 'interests')

    if data_dict.get('user_notified'):
        profile.user_notified = data_dict.get('user_notified')

    profile.save()
    model.Session.flush()

    try:
        user_profile_service.clear_cached(user_id)
    except Exception as e:
        log.warning('Failed to clear cached data for user %s. Error: %s',
                    user_id, str(e))

    return _table_dictize(profile, context)


def notifications_read(context, data_dict):
    '''Marks a list of notifications as read.

    The notifications must belong to this user (from context). Those that don't
    and belong to a different user will not be marked as read.

    :param notifications: `list` of notification IDs to mark as read. If not
        specified, ALL notifications for the current user will be marked as
        read.
    '''
    check_access('notifications_read', context)
    user = context.get('auth_user_obj')

    Notification.mark_read(user.id, data_dict.get('notifications'))

    return {}
