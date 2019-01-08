import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.knowledgehub.helpers import _register_blueprints

class KnowledgehubPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'knowledgehub')

    # IBlueprint
    def get_blueprint(self):
        return _register_blueprints()
