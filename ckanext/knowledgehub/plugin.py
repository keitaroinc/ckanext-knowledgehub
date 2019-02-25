import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultDatasetForm

import ckanext.knowledgehub.helpers as h
from ckanext.knowledgehub.model.theme import theme_db_setup

from ckanext.knowledgehub.helpers import _register_blueprints
from ckanext.knowledgehub.model.research_question import setup as rq_db_setup
from ckanext.knowledgehub.model.sub_theme import setup as sub_theme_db_setup
#from ckanext.knowledgehub.helpers import resource_view_get_fields


class KnowledgehubPlugin(plugins.SingletonPlugin, DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm)

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
	    'resource_view_get_fields': h.resource_view_get_fields
        }

    # IDatasetForm
    def _modify_package_schema(self, schema):
        defaults = [toolkit.get_validator('ignore_missing')]

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
        return self._modify_package_schema(schema)

    def is_fallback(self):
        return True

    def package_types(self):
        return []
