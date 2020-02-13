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
from ckanext.knowledgehub.model import ResourceValidate
from ckanext.knowledgehub.model import ResourceValidation
from ckanext.knowledgehub.model import Dashboard
from ckanext.knowledgehub.model import KWHData
from ckanext.knowledgehub.model import Visualization
from ckanext.knowledgehub.model import UserIntents, DataQualityMetrics
from ckanext.knowledgehub.model import Keyword
from ckanext.knowledgehub.backend.factory import get_backend
from ckanext.knowledgehub.lib.writer import WriterService
from ckanext.knowledgehub import helpers as plugin_helpers
from ckanext.knowledgehub.logic.jobs import schedule_data_quality_check


log = logging.getLogger(__name__)

_df = lib.navl.dictization_functions
_table_dictize = lib.dictization.table_dictize
_get_or_bust = logic.get_or_bust

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
            sub_theme_data.get('id'), str(e)
        ))

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
                rq_data.get('id'), str(e)
        ))

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

    if not data_dict['tags']:
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
            'Unable to update visualization %s in knowledgehub data: %s'
                % (resource_view_data.get('id'), str(e))
            )

    # this check is done for the unit tests
    if resource_view_data.get('__extras'):
        ext = resource_view_data['__extras']
        ext_old = resource_view_data['__extras']
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

    items = ['name', 'title', 'description', 'indicators', 'source', 'type', 'tags']

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
    result = ckan_package_update(context, data_dict)
    schedule_data_quality_check(result['id'])

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
    :type filter: string
    :returns: the updated data
    :rtype: dict
    '''
    check_access('kwh_data', context, data_dict)

    session = context['session']

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
    for dimension in  dimensions:
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
                        raise ValidationError({field: _('Invalid Value' + "(%s) '%s'" % (dimension, value))})
                else:
                    try:
                        values[field] = _ftype(value)
                    except:
                        raise ValidationError({field: _('Invalid Value Type')})
    db_metric = DataQualityMetrics.get(_type, data_dict['id'])
    if not db_metric:
        db_metric = DataQualityMetrics(type=_type, ref_id=data_dict['id'])

    db_metric.metrics = db_metric.metrics or {}

    for field, values in data_dict.items():
        if not field in dimensions:
            continue
        setattr(db_metric, field, values['value']) # set the main metric
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

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.resource_validation_schema(),
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

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.resource_validation_schema(),
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

    data, errors = _df.validate(data_dict,
                                knowledgehub_schema.resource_validation_schema(),
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

    tag = model.Tag.get(data.get('id'))
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

    :param name: `str`, the name of the keyword to update.
    :param tags: `list` of `str`, the tags that this keyword should contain. If
        the tag does not exist, it will be created and added to this keyword.
        The tags that were removed from this keyword will be set as free tags
        and will not be removed.

    :returns: `dict`, the updated keyword.
    '''
    check_access('keyword_update', context)
    if 'name' not in data_dict:
        raise ValidationError({'name': _('Missing Value')})

    existing = Keyword.by_name(data_dict['name'])
    if not existing:
        raise logic.NotFound(_('Not found'))

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
            tag_dict = toolkit.get_action('tag_create')(context, {
                'name': tag,
            })

        db_tag = model.Tag.get(tag_dict['id'])
        db_tag.keyword_id = existing.id
        db_tag.save()
        tag_dict = _table_dictize(db_tag, context)
        kwd_dict['tags'].append(tag_dict)

    return kwd_dict
