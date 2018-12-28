import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.knowledgehub.model import af_db_setup
from ckanext.knowledgehub import actions as knowledgehub_actions
from ckanext.knowledgehub import auth as knowledgehub_auth


class KnowledgehubPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'knowledgehub')

    # IConfigurable
    def configure(self, config):
        af_db_setup()
        return config

   # IActions
    def get_actions(self):
        return {
            'analytical_framework_delete': knowledgehub_actions.analytical_framework_delete,
            'analytical_framework_list': knowledgehub_actions.analytical_framework_list,
        }

    # IAuthFunctions
    def get_auth_functions(self):
        return {
            'analytical_framework_delete': knowledgehub_auth.analytical_framework_delete,
            'analytical_framework_list': knowledgehub_actions.analytical_framework_list,
        }
