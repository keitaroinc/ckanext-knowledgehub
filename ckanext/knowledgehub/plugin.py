import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultDatasetForm

import ckanext.knowledgehub.helpers as h

from ckanext.knowledgehub.helpers import _register_blueprints


class KnowledgehubPlugin(plugins.SingletonPlugin, DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IPackageController, inherit=True)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'knowledgehub')

    # IConfigurable
    def configure(self, config):
        return config

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
            'pg_array_to_py_list': h.pg_array_to_py_list,
        }

    # IDatasetForm
    def _modify_package_schema(self, schema):
        defaults = [toolkit.get_validator('ignore_missing')]

        schema.update({
            'theme': [toolkit.get_validator('ignore_missing'),
                      toolkit.get_converter('convert_to_extras'),
                      toolkit.get_converter('convert_to_list_if_string')],
            'sub_theme': [toolkit.get_validator('ignore_missing'),
                          toolkit.get_converter('convert_to_extras'),
                          toolkit.get_converter('convert_to_list_if_string')],
            'research_question': [toolkit.get_validator('ignore_missing'),
                                  toolkit.get_converter('convert_to_extras'),
                                  ]
        })

        schema['resources'].update({
            'db_type': defaults,
            'db_name': defaults,
            'host': defaults,
            'port': defaults,
            'username': defaults,
            'password': defaults,
            'sql': defaults,
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
        schema.update({
            'theme': [toolkit.get_converter('convert_from_extras'),
                      toolkit.get_validator('ignore_missing')],
            'sub_theme': [toolkit.get_converter('convert_from_extras'),
                          toolkit.get_validator('ignore_missing')],
            'research_question': [toolkit.get_converter('convert_from_extras'),
                                  toolkit.get_validator('ignore_missing')]
        })
        schema['resources'].update({
            'db_type': defaults,
            'db_name': defaults,
            'host': defaults,
            'port': defaults,
            'username': defaults,
            'password': defaults,
            'sql': defaults,
        })
        return schema

    def is_fallback(self):
        return True

    def package_types(self):
        return []

    # IPackageController
    def before_index(self, data_dict):
        return data_dict
