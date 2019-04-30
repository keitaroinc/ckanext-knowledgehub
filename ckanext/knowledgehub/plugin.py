import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultDatasetForm

import ckanext.knowledgehub.helpers as h

from ckanext.knowledgehub.helpers import _register_blueprints


class KnowledgehubPlugin(plugins.SingletonPlugin, DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IRoutes, inherit=True)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'knowledgehub')

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
            'get_map_config': h.get_map_config
        }

    # IDatasetForm
    def _modify_package_schema(self, schema):
        defaults = [toolkit.get_validator('ignore_missing')]
        package_defaults = [toolkit.get_validator('ignore_missing'),
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
            'research_question': package_defaults
        })

        schema['resources'].update({
            'db_type': defaults,
            'db_name': defaults,
            'host': defaults,
            'port': defaults,
            'username': defaults,
            'password': defaults,
            'sql': defaults
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
            'research_question': package_defaults
        })

        schema['resources'].update({
            'db_type': defaults,
            'db_name': defaults,
            'host': defaults,
            'port': defaults,
            'username': defaults,
            'password': defaults,
            'sql': defaults
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
        return map
