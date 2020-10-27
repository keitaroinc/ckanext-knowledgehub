from hdx.hdx_configuration import Configuration
import json
from logging import getLogger

from routes.mapper import SubMapper

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan import logic
from ckan.lib.plugins import DefaultDatasetForm, DefaultPermissionLabels
from ckan.common import config
from ckan.lib.base import BaseController as CKANBaseController

# imports for DatastoreBackend
from ckanext.datastore.backend.postgres import DatastorePostgresqlBackend
import ckanext.datastore.interfaces as interfaces
from ckanext.datastore.backend.postgres import get_write_engine
from ckanext.datastore.backend.postgres import _cache_types
from ckanext.datastore.backend.postgres import _rename_json_field
from sqlalchemy.exc import (ProgrammingError, IntegrityError,
                            DBAPIError, DataError)
from ckanext.datastore.backend.postgres import check_fields
from ckanext.datastore.backend.postgres import _pluck
from ckanext.datastore.backend.postgres import identifier
from ckanext.datastore.backend.postgres import _create_fulltext_trigger
from ckanext.datastore.backend.postgres import insert_data
from ckanext.datastore.backend.postgres import create_indexes
from ckanext.datastore.backend.postgres import create_alias
from ckanext.datastore.backend.postgres import _unrename_json_field
from ckanext.datastore.backend.postgres import _guess_type
from ckanext.datapusher.interfaces import IDataPusher

import ckanext.knowledgehub.helpers as h
from ckanext.knowledgehub.helpers import _register_blueprints
from ckanext.knowledgehub.lib.search import patch_ckan_core_search
from ckanext.knowledgehub.model.keyword import extend_tag_table
from ckanext.knowledgehub.model.visualization import extend_resource_view_table
from ckanext.knowledgehub.model.dashboard import dashboard_table_upgrade
from ckanext.knowledgehub.lib.util import get_as_list


from ckanext.datastore.backend import (
    DatastoreException,
    _parse_sort_clause,
    DatastoreBackend
)


ValidationError = logic.ValidationError

_TIMEOUT = 60000  # milliseconds
_DB_INITIALIZED = False

log = getLogger(__name__)


def _init_knowledgehub_database():
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        log.debug('Database already initialized')
        return

    from ckanext.knowledgehub.cli.db import init_db

    init_db()


def _patch_ckan_base_controller():
    original_before = CKANBaseController.__before__

    def wrapped_before(*args, **kwagrs):
        result = original_before(*args, **kwagrs)
        try:
            h.log_request()
        except Exception as e:
            log.exception(e)
        return result

    CKANBaseController.__before__ = wrapped_before


class KnowledgehubPlugin(plugins.SingletonPlugin, DefaultDatasetForm,
                         DefaultPermissionLabels):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(interfaces.IDatastoreBackend, inherit=True)
    plugins.implements(plugins.IAuthenticator, inherit=True)
    plugins.implements(plugins.IPermissionLabels)
    plugins.implements(IDataPusher, inherit=True)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'knowledgehub')

        # Eliminates the need to re-initialize the database when model changes.
        _init_knowledgehub_database()
        _patch_ckan_base_controller()

        # patch the CKAN core functionality
        patch_ckan_core_search()
        # Extend CKAN Tag table
        extend_tag_table()
        # Extend CKAN ResourceView table
        extend_resource_view_table()
        # Upgrade the dashboard table.
        dashboard_table_upgrade()

        DatastoreBackend.register_backends()
        # DatastoreBackend.set_active_backend(config)

        # Create the HDX configuration
        hdx_api_key = config.get(u'ckanext.knowledgehub.hdx.api_key')
        hdx_site = config.get(u'ckanext.knowledgehub.hdx.site', 'test')
        Configuration.delete()
        Configuration.create(
            hdx_site=hdx_site,  # from config, default to test
            user_agent='admin',
            hdx_key=hdx_api_key
        )


    # IBlueprint
    def get_blueprint(self):
        return _register_blueprints()

    # IActions
    def get_actions(self):
        module_root = 'ckanext.knowledgehub.logic.action'
        action_functions = h._get_functions(module_root)

        return action_functions

    # IAuthFunctions
    def get_auth_functions(self):
        module_root = 'ckanext.knowledgehub.logic.auth'
        auth_functions = h._get_functions(module_root)

        # When setting the auth function, CKAN will try to authorize every call
        # to the action, which is not desireable for package search.
        auth_functions.pop('package_search')

        return auth_functions

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'id_to_title': h.id_to_title,
            'get_rq_options': h.get_rq_options,
            'get_theme_options': h.get_theme_options,
            'get_sub_theme_options': h.get_sub_theme_options,
            'resource_view_get_fields': h.resource_view_get_fields,
            'get_resource_columns': h.get_resource_columns,
            'get_chart_types': h.get_chart_types,
            'get_uuid': h.get_uuid,
            'get_visualization_size': h.get_visualization_size,
            'get_color_scheme': h.get_color_scheme,
            'get_map_color_scheme': h.get_map_color_scheme,
            'parse_json': h.parse_json,
            'get_chart_sort': h.get_chart_sort,
            'get_tick_text_rotation': h.get_tick_text_rotation,
            'get_data_formats': h.get_data_formats,
            'dump_json': h.dump_json,
            'get_resource_data': h.get_resource_data,
            'get_resource_numeric_columns': h.get_resource_numeric_columns,
            'get_filter_values': h.get_filter_values,
            'get_rq': h.get_rq,
            'resource_view_icon': h.resource_view_icon,
            'get_last_visuals': h.get_last_visuals,
            'pg_array_to_py_list': h.pg_array_to_py_list,
            'knowledgehub_get_map_config': h.knowledgehub_get_map_config,
            'knowledgehub_get_geojson_resources': h.get_geojson_resources,
            'rq_ids_to_titles': h.rq_ids_to_titles,
            'knowledgehub_get_dataset_url_path': h.get_dataset_url_path,
            'resource_feedback_count': h.resource_feedback_count,
            'get_rq_ids': h.get_rq_ids,
            'get_rq_titles_from_res': h.get_rq_titles_from_res,
            'get_dashboards': h.get_dashboards,
            'knowledgehub_get_geojson_properties': h.get_geojson_properties,
            'get_single_rq': h.get_single_rq,
            'get_rqs_dashboards': h.get_rqs_dashboards,
            'remove_space_for_url': h.remove_space_for_url,
            'format_date': h.format_date,
            'get_searched_rqs': h.get_searched_rqs,
            'get_searched_dashboards': h.get_searched_dashboards,
            'get_searched_visuals': h.get_searched_visuals,
            'dashboard_research_questions': h.dashboard_research_questions,
            'add_rqs_to_dataset': h.add_rqs_to_dataset,
            'remove_rqs_from_dataset': h.remove_rqs_from_dataset,
            'update_rqs_in_dataset': h.update_rqs_in_dataset,
            'get_single_dash': h.get_single_dash,
            'get_active_tab': h.get_active_tab,
            'get_tab_url': h.get_tab_url,
            'is_rsc_upload_datastore': h.is_rsc_upload_datastore,
            'get_dataset_data': h.get_dataset_data,
            'get_resource_filtered_data': h.get_resource_filtered_data,
            'get_package_data_quality': h.get_package_data_quality,
            'get_resource_data_quality': h.get_resource_data_quality,
            'get_resource_validation_data': h.get_resource_validation_data,
            'get_resource_validation_options':
                h.get_resource_validation_options,
            'check_resource_status': h.check_resource_status,
            'check_validation_admin': h.check_validation_admin,
            'keyword_list': h.keyword_list,
            'get_datasets': h.get_datasets,
            'get_notifications': h.get_notifications,
            'get_all_users': h.get_all_users,
            'get_all_organizations': h.get_all_organizations,
            'get_all_groups': h.get_all_groups,
            'calculate_time_passed': h.calculate_time_passed,
            'check_if_dataset_is_on_hdx': h.check_if_dataset_is_on_hdx,
            'human_elapsed_time': h.human_elapsed_time,
            'get_requested_resource_type_and_ref':
                h.get_requested_resource_type_and_ref,
            'get_comments_count': h.get_comments_count,
            'get_countries': h.get_countries,
        }

    # IDatasetForm
    def _modify_package_schema(self, schema):
        defaults = [toolkit.get_validator('ignore_missing')]
        package_defaults = [toolkit.get_validator('ignore_missing'),
                            toolkit.get_converter('convert_to_extras')]
        mandatory_defaults = [toolkit.get_validator('not_empty'), 
                            toolkit.get_converter('convert_to_extras')]

        schema.update({
            'unit_supported': package_defaults,
            'im_product_name': package_defaults,
            'indicator_label': package_defaults,
            'indicator_code': package_defaults,
            'indicator_old_name': package_defaults,
            'unit_focal_point': package_defaults,
            'sector': package_defaults,
            'data_sources': package_defaults,
            'frequency_of_update': package_defaults,
            'sub_themes': package_defaults,
            'analytical_value': package_defaults,
            'indicator_type': package_defaults,
            'theme': package_defaults,
            'sub_theme': package_defaults,
            'research_question': package_defaults,
            'country_code_displacement': package_defaults,
            'country_code_origin': package_defaults,
            'shared_with_users': package_defaults,
            'shared_with_organizations': package_defaults,
            'shared_with_groups': package_defaults,
            'hdx_name': package_defaults,
            'short_title': package_defaults,
            'data_sensitivity': package_defaults,
            'external_access': package_defaults,
            'original_id': package_defaults,
            'date_range_start': package_defaults,
            'date_range_end': package_defaults,
            'unit_of_measurement': mandatory_defaults,
            'sampling_procedure': package_defaults,
            'operational_purpose': package_defaults,
            'archived': mandatory_defaults,
            'admin_notes': package_defaults,
            'sampling_procedure_notes': package_defaults,
            'response_rate_notes': package_defaults,
            'data_collection_notes': package_defaults,
            'weight_notes': package_defaults,
            'clean_ops_notes': package_defaults,
            'data_access_notes': package_defaults,
            'hxl_ated': package_defaults,
            'process_status': package_defaults,
            'identifiability': package_defaults,
            'geog_coverage': package_defaults,
            'data_collection_technique': mandatory_defaults,
            'linked_datasets': package_defaults,
            'data_collector': mandatory_defaults,

        })

        schema['resources'].update({
            'db_type': defaults,
            'db_name': defaults,
            'host': defaults,
            'port': defaults,
            'username': defaults,
            'password': defaults,
            'sql': defaults,
            'date_range_start': mandatory_defaults,
            'date_range_end': mandatory_defaults,
            'process_status': mandatory_defaults,
            'identifiability': mandatory_defaults,
            'hxl_ated': mandatory_defaults,
            'file_type': mandatory_defaults,
        })

        return schema

    def create_package_schema(self):
        schema = super(KnowledgehubPlugin, self).create_package_schema()
        return self._modify_package_schema(schema)

    def update_package_schema(self):
        schema = super(KnowledgehubPlugin, self).update_package_schema()
        return self._modify_package_schema(schema)

    def show_package_schema(self):
        schema = super(KnowledgehubPlugin, self).show_package_schema()
        defaults = [toolkit.get_validator('ignore_missing')]
        package_defaults = [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
        mandatory_defaults = [toolkit.get_validator('not_empty'),
                            toolkit.get_converter('convert_from_extras')]

        schema.update({
            'unit_supported': package_defaults,
            'im_product_name': package_defaults,
            'indicator_label': package_defaults,
            'indicator_code': package_defaults,
            'indicator_old_name': package_defaults,
            'unit_focal_point': package_defaults,
            'sector': package_defaults,
            'data_sources': package_defaults,
            'frequency_of_update': package_defaults,
            'analytical_value': package_defaults,
            'indicator_type': package_defaults,
            'theme': package_defaults,
            'sub_theme': package_defaults,
            'research_question': package_defaults,
            'country_code_displacement': package_defaults,
            'country_code_origin': package_defaults,
            'shared_with_users': package_defaults,
            'shared_with_organizations': package_defaults,
            'shared_with_groups': package_defaults,
            'hdx_name': package_defaults,
            'short_title': package_defaults,
            'data_sensitivity': package_defaults,
            'external_access': package_defaults,
            'original_id': package_defaults,
            'date_range_start': package_defaults,
            'date_range_end': package_defaults,
            'unit_of_measurement': package_defaults,
            'sampling_procedure': package_defaults,
            'operational_purpose': package_defaults,
            'archived': package_defaults,
            'admin_notes': package_defaults,
            'sampling_procedure_notes': package_defaults,
            'response_rate_notes': package_defaults,
            'data_collection_notes': package_defaults,
            'weight_notes': package_defaults,
            'clean_ops_notes': package_defaults,
            'data_access_notes': package_defaults,
            'hxl_ated': package_defaults,
            'process_status': package_defaults,
            'identifiability': package_defaults,
            'geog_coverage': package_defaults,
            'data_collection_technique': package_defaults,
            'linked_datasets': package_defaults,
            'data_collector': package_defaults,

        })

        schema['resources'].update({
            'db_type': defaults,
            'db_name': defaults,
            'host': defaults,
            'port': defaults,
            'username': defaults,
            'password': defaults,
            'sql': defaults,
            'dq_timeliness_column': defaults,
            'dq_timeliness_date_format': defaults,
            'dq_accuracy_column': defaults,
            'data_quality_completeness_column': defaults,
            'hdx_name_resource': defaults,
            'date_range_start': mandatory_defaults,
            'date_range_end': mandatory_defaults,
            'process_status': mandatory_defaults,
            'identifiability': mandatory_defaults,
            'hxl_ated': mandatory_defaults,
            'file_type': mandatory_defaults,
        })
        return schema

    def is_fallback(self):
        return True

    def package_types(self):
        return []

    # IRoutes
    def before_map(self, map):
        map.redirect('/', '/dataset',
                     _redirect_code='301 Moved Permanently')
        # Override the package search action.
        with SubMapper(
            map,
            controller='ckanext.knowledgehub.controllers:KWHPackageController'
        ) as m:
            m.connect('search', '/dataset', action='search',
                      highlight_actions='index search')
            m.connect('dataset_new', '/dataset/new', action='new')
            m.connect('/dataset/{action}',
                      requirements=dict(action='|'.join([
                          'list',
                          'autocomplete',
                          'search'
                      ])))

            m.connect('/dataset/{action}/{id}/{revision}', action='read_ajax',
                      requirements=dict(action='|'.join([
                          'read',
                          'edit',
                          'history',
                      ])))
            m.connect('/dataset/{action}/{id}',
                      requirements=dict(action='|'.join([
                          'new_resource',
                          'history',
                          'read_ajax',
                          'history_ajax',
                          'follow',
                          'activity',
                          'groups',
                          'unfollow',
                          'delete',
                          'api_data',
                      ])))
            m.connect('dataset_edit', '/dataset/edit/{id}', action='edit',
                      ckan_icon='pencil-square-o')
            m.connect('dataset_followers', '/dataset/followers/{id}',
                      action='followers', ckan_icon='users')
            m.connect('dataset_activity', '/dataset/activity/{id}',
                      action='activity', ckan_icon='clock-o')
            m.connect('/dataset/activity/{id}/{offset}', action='activity')
            m.connect('dataset_groups', '/dataset/groups/{id}',
                      action='groups', ckan_icon='users')
            m.connect('dataset_resources', '/dataset/resources/{id}',
                      action='resources', ckan_icon='bars')
            m.connect('dataset_read', '/dataset/{id}', action='read',
                      ckan_icon='sitemap')
            m.connect('/dataset/{id}/resource/{resource_id}',
                      action='resource_read')
            m.connect('resource_validation_status',
                      '/dataset/{id}/resource/{resource_id}/validate-resource',
                      action='resource_validation_status')
            m.connect('resource_validation_revert',
                      '/dataset/{id}/resource/{resource_id}/invalidate-resource',
                      action='resource_validation_revert')
            m.connect('/dataset/{id}/resource_delete/{resource_id}',
                      action='resource_delete')
            m.connect('resource_edit', '/dataset/{id}/resource_edit/{resource_id}',
                      action='resource_edit', ckan_icon='pencil-square-o')
            m.connect('/dataset/{id}/resource/{resource_id}/download',
                      action='resource_download')
            m.connect('/dataset/{id}/resource/{resource_id}/download/{filename}',
                      action='resource_download')
            m.connect('/dataset/{id}/resource/{resource_id}/embed',
                      action='resource_embedded_dataviewer')
            m.connect('/dataset/{id}/resource/{resource_id}/viewer',
                      action='resource_embedded_dataviewer', width="960",
                      height="800")
            m.connect('/dataset/{id}/resource/{resource_id}/preview',
                      action='resource_datapreview')
            m.connect('views', '/dataset/{id}/resource/{resource_id}/views',
                      action='resource_views', ckan_icon='bars')
            m.connect('new_view', '/dataset/{id}/resource/{resource_id}/new_view',
                      action='edit_view', ckan_icon='pencil-square-o')
            m.connect('edit_view',
                      '/dataset/{id}/resource/{resource_id}/edit_view/{view_id}',
                      action='edit_view', ckan_icon='pencil-square-o')
            m.connect('resource_view',
                      '/dataset/{id}/resource/{resource_id}/view/{view_id}',
                      action='resource_view')
            m.connect('/dataset/{id}/resource/{resource_id}/view/',
                      action='resource_view')

        # Override read action, for changing the titles in facets and tell CKAN
        #  where to look for new and list actions.
        # NOTE: List and New actions should be specified before Read action!!
        with SubMapper(
            map,
            controller='ckanext.knowledgehub.controllers:KWHGroupController'
        ) as m:
            m.connect('group_list', '/group/list', action='list')
            m.connect('group_new', '/group/new', action='new')
            m.connect('group_delete', '/group/delete' +
                      '/{id}', action='delete')
            m.connect('group_read', '/group/{id}', action='read')

        with SubMapper(
            map,
            controller='ckanext.knowledgehub.controllers:KWHOrganizationController'
        ) as m:
            m.connect('organization_new', '/organization/new', action='new')
            m.connect('organization_delete',
                      '/organization/delete' + '/{id}', action='delete')

            m.connect('organization_read', '/organization/{id}', action='read')
            m.connect('organization_bulk_process',
                      '/organization/bulk_process/{id}', action='bulk_process')

        with SubMapper(
            map,
            controller='ckanext.oauth2.controller:OAuth2Controller'
        ) as m:
            m.connect('user_login_azure', '/user/login/azure', action='login')

        return map

    # IPackageController
    def before_index(self, pkg_dict):
        validated_data = None
        try:
            validated_data = json.loads(pkg_dict.get('validated_data_dict',
                                                     '{}'))
            pkg_dict['idx_tags'] = []
            keywords = []
            for tag in validated_data.get('tags', []):
                if tag.get('keyword_id'):
                    keywords.append(tag['keyword_id'])
                pkg_dict['idx_tags'].append(tag.get('name'))

            extras_keywords = []
            for keyword in keywords:
                try:
                    keyword = toolkit.get_action('keyword_show')({
                        'ignore_auth': True,
                    }, {
                        'id': keyword,
                    })
                    extras_keywords.append(keyword['name'])
                except Exception as e:
                    log.warning('Failed to get keyword %s. Error: %s',
                                keyword,
                                str(e))
                    log.exception(e)

            pkg_dict['extras_keywords'] = ','.join(extras_keywords)
            pkg_dict['idx_keywords'] = keywords

        except Exception as e:
            log.warn("Failed to extract keyword for dataset '%s'. Error: %s",
                     pkg_dict.get('id'), str(e))

        research_questions = set()
        if validated_data:
            for resource in validated_data.get('resources', []):
                try:
                    resource_views = toolkit.get_action('resource_view_list')({
                        'ignore_auth': True,
                    }, {
                        'id': resource['id']
                    })
                    for resource_view in resource_views:
                        if resource_view.get('view_type') != 'recline_view':
                            rqs = resource_view.get('__extras', {}).\
                                get('research_questions', '')
                            if isinstance(rqs, str) or \
                                    isinstance(rqs, unicode):
                                rqs = map(lambda r: r.strip(),
                                          filter(lambda r: r and r.strip(),
                                                 rqs.split(',')))
                            if rqs:
                                for rq in rqs:
                                    try:
                                        rq = toolkit.get_action(
                                            'research_question_show')({
                                                'ignore_auth': True,
                                            }, {
                                                'id': rq
                                            })
                                        research_questions.add(rq['id'])
                                    except Exception as e:
                                        log.debug('Failed to get research '
                                                  'question %s. Error: %s',
                                                  rq,
                                                  str(e))
                except Exception as e:
                    log.debug('Failed to load research question. Error: %s',
                              str(e))
                    log.exception(e)

        research_questions = ','.join(research_questions)
        pkg_dict['research_question'] = research_questions
        pkg_dict['extras_research_question'] = research_questions
        pkg_dict['idx_research_questions'] = research_questions

        return pkg_dict

    # IDatastoreBackend
    def register_backends(self):
        return {
            'postgresql': DatastorePostgresqlBackend,
            'postgres': DatastorePostgresqlBackend,
        }

    # IAuthenticator
    def identify(self):
        from ckan.common import is_flask_request
        if not is_flask_request():
            h.check_user_profile_preferences()
        return super(KnowledgehubPlugin, self).identify()

    # IPermissionLabels
    def get_dataset_labels(self, dataset_obj):
        if dataset_obj.state == u'active' and not dataset_obj.private:
            return [u'public']

        if dataset_obj.owner_org:
            labels = [u'member-%s' % dataset_obj.owner_org]
            shared_with_users = dataset_obj.extras.get('shared_with_users')
            if isinstance(shared_with_users, unicode):
                if shared_with_users.startswith('{') and \
                        shared_with_users.endswith('}'):
                    labels.extend(
                        list(map(
                            lambda user: 'user-%s' % user,
                            filter(lambda user: user and user.strip(),
                                   shared_with_users[1:-1].split(','))))
                    )
                else:
                    if shared_with_users.strip():
                        labels.append(u'user-%s' % shared_with_users.strip())
            if isinstance(shared_with_users, list):
                labels.extend(
                    list(map(lambda user: 'user-%s' % user,
                             filter(lambda user: user and user.strip(),
                                    shared_with_users)))
                )

            shared_with_organizations = get_as_list(
                'shared_with_organizations', dataset_obj.extras)
            shared_with_groups = get_as_list('shared_with_groups',
                                             dataset_obj.extras)

            for group_id in shared_with_groups + shared_with_organizations:
                labels.append('member-%s' % group_id)

            return labels

        return [u'creator-%s' % dataset_obj.creator_user_id]

    def get_user_dataset_labels(self, user_obj):
        labels = [u'public']
        if not user_obj:
            return labels

        labels.append(u'creator-%s' % user_obj.id)
        labels.append(u'user-%s' % user_obj.name)
        labels.append(u'user-%s' % user_obj.id)

        orgs = logic.get_action(u'organization_list_for_user')(
            {u'user': user_obj.id}, {u'permission': u'read'})
        labels.extend(u'member-%s' % o[u'id'] for o in orgs)

        groups = logic.get_action('group_list_for_user')({
            'ignore_auth': True,
        }, {
            'user': user_obj.id,
        })
        labels.extend(u'member-%s' % g[u'id'] for g in groups)

        return labels

    # IDataPusher
    def after_upload(self, context, resource_dict, dataset_dict):
        from ckanext.knowledgehub.logic.jobs import schedule_data_quality_check

        schedule_data_quality_check(dataset_dict['id'], force_recalculate=True)


class DatastorePostgresqlBackend(DatastorePostgresqlBackend):

    def create(self, context, data_dict):
        '''
        The first row will be used to guess types not in the fields and the
        guessed types will be added to the headers permanently.
        Consecutive rows have to conform to the field definitions.
        rows can be empty so that you can just set the fields.
        fields are optional but needed if you want to do type hinting or
        add extra information for certain columns or to explicitly
        define ordering.
        eg: [{"id": "dob", "type": "timestamp"},
             {"id": "name", "type": "text"}]
        A header items values can not be changed after it has been defined
        nor can the ordering of them be changed. They can be extended though.
        Any error results in total failure! For now pass back the actual error.
        Should be transactional.
        :raises InvalidDataError: if there is an invalid value in the given
                                  data
        '''
        engine = get_write_engine()
        context['connection'] = engine.connect()
        timeout = context.get('query_timeout', _TIMEOUT)
        _cache_types(context)

        _rename_json_field(data_dict)

        trans = context['connection'].begin()
        try:
            # check if table already existes
            context['connection'].execute(
                u'SET LOCAL statement_timeout TO {0}'.format(timeout))
            result = context['connection'].execute(
                u'SELECT * FROM pg_tables WHERE tablename = %s',
                data_dict['resource_id']
            ).fetchone()
            if not result:
                create_table_knowledgehub(context, data_dict)
                _create_fulltext_trigger(
                    context['connection'],
                    data_dict['resource_id'])
            else:
                alter_table(context, data_dict)
            if 'triggers' in data_dict:
                _create_triggers(
                    context['connection'],
                    data_dict['resource_id'],
                    data_dict['triggers'])
            insert_data(context, data_dict)
            create_indexes(context, data_dict)
            create_alias(context, data_dict)
            trans.commit()
            return _unrename_json_field(data_dict)
        except IntegrityError as e:
            if e.orig.pgcode == _PG_ERR_CODE['unique_violation']:
                raise ValidationError({
                    'constraints': ['Cannot insert records or create index'
                                    'because of uniqueness constraint'],
                    'info': {
                        'orig': str(e.orig),
                        'pgcode': e.orig.pgcode
                    }
                })
            raise
        except DataError as e:
            raise ValidationError({
                'data': e.message,
                'info': {
                    'orig': [str(e.orig)]
                }})
        except DBAPIError as e:
            if e.orig.pgcode == _PG_ERR_CODE['query_canceled']:
                raise ValidationError({
                    'query': ['Query took too long']
                })
            raise
        except Exception as e:
            trans.rollback()
            raise
        finally:
            context['connection'].close()


def create_table_knowledgehub(context, data_dict):
    '''Creates table, columns and column info (stored as comments).

    :param resource_id: The resource ID (i.e. postgres table name)
    :type resource_id: string
    :param fields: details of each field/column, each with properties:
        id - field/column name
        type - optional, otherwise it is guessed from the first record
        info - some field/column properties, saved as a JSON string in postgres
            as a column comment. e.g. "type_override", "label", "notes"
    :type fields: list of dicts
    :param records: records, of which the first is used when a field type needs
        guessing.
    :type records: list of dicts
    '''

    datastore_fields = [
        {'id': '_id', 'type': 'serial primary key'},
        {'id': '_full_text', 'type': 'tsvector'},
    ]

    # check first row of data for additional fields
    extra_fields = []
    supplied_fields = data_dict.get('fields', [])
    check_fields(context, supplied_fields)
    field_ids = _pluck('id', supplied_fields)
    records = data_dict.get('records')

    fields_errors = []

    for field_id in field_ids:
        # Postgres has a limit of 63 characters for a column name
        if len(field_id) > 63:
            raise ValidationError({
                'field': ['Column heading exceeds limit of '
                          '63 characters. "{0}" '.format(field_id)]
            })

    if fields_errors:
        raise ValidationError({
            'fields': fields_errors
        })
    # if type is field is not given try and guess or throw an error
    for field in supplied_fields:
        if 'type' not in field:
            if not records or field['id'] not in records[0]:
                raise ValidationError({
                    'fields': [u'"{0}" type not guessable'.format(field['id'])]
                })
            field['type'] = _guess_type(records[0][field['id']])

    # Check for duplicate fields
    unique_fields = set([f['id'] for f in supplied_fields])
    if not len(unique_fields) == len(supplied_fields):
        all_duplicates = set()
        field_ids = _pluck('id', supplied_fields)
        for field_id in field_ids:
            if field_ids.count(field_id) > 1:
                all_duplicates.add(field_id)
        string_fields = ", ".join(all_duplicates)
        raise ValidationError({
            'field': ['Duplicate column names are not supported! '
                      'Duplicate columns are : "{0}" '.format(string_fields)]
        })

    if records:
        # check record for sanity
        if not isinstance(records[0], dict):
            raise ValidationError({
                'records': ['The first row is not a json object']
            })
        supplied_field_ids = records[0].keys()
        for field_id in supplied_field_ids:
            if field_id not in field_ids:
                extra_fields.append({
                    'id': field_id,
                    'type': _guess_type(records[0][field_id])
                })

    fields = datastore_fields + supplied_fields + extra_fields
    sql_fields = u", ".join([u'{0} {1}'.format(
        identifier(f['id']), f['type']) for f in fields])

    sql_string = u'CREATE TABLE {0} ({1});'.format(
        identifier(data_dict['resource_id']),
        sql_fields
    )

    info_sql = []
    for f in supplied_fields:
        info = f.get(u'info')
        if isinstance(info, dict):
            info_sql.append(u'COMMENT ON COLUMN {0}.{1} is {2}'.format(
                identifier(data_dict['resource_id']),
                identifier(f['id']),
                literal_string(
                    json.dumps(info, ensure_ascii=False))))

    context['connection'].execute(
        (sql_string + u';'.join(info_sql)).replace(u'%', u'%%'))
