import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckanext.knowledgehub.helpers as h

from ckanext.knowledgehub.helpers import _register_blueprints
from ckanext.knowledgehub.model.sub_theme import setup as sub_theme_db_setup


class KnowledgehubPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'knowledgehub')

    # IConfigurable
    def configure(self, config):
        # Initialize DB
        sub_theme_db_setup()

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
