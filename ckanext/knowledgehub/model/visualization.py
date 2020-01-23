from ckan.model import ResourceView, resource_view_table
from ckan.model.meta import mapper
from ckan.logic import get_action

from ckanext.knowledgehub.lib.solr import Indexed, mapped
import json

class Visualization(ResourceView, Indexed):

    indexed = [
        mapped('id', 'entity_id'),
        'resource_id',
        'title',
        'description',
        'view_type',
        'research_questions',
        'package_id',
	    mapped('organization', 'organization'),
        mapped('groups', 'groups')
    ]

    doctype = 'visualization'

    @staticmethod
    def before_index(data):
	    package_id = data.get('package_id')
        package = get_action('package_show')(
            {'ignore_auth': True},
            {'id': package_id, 'include_tracking': True}
        )
        if package:
            data['organization'] = package.get('organization', {}).get('name')

            data['groups'] = []
            for g in package.get('groups', []):
                data['groups'].append(g['name'])

        if data.get('_sa_instance_state'):
            del data['_sa_instance_state']
        if data.get('description') is not None:
            return data

        def _get_description(data_dict):
            if not data_dict.get('__extras'):
                return None
            extras = data_dict['__extras']
            if data['view_type'] == 'chart':
                    return extras.get('chart_description', '')
            elif data['view_type'] == 'table':
                return extras.get('table_description', '')
            elif data['view_type'] == 'map':
                return extras.get('map_description', '')
            else:
                # guess the description
                for prop, value in extras.items():
                    if prop == 'description' or prop.endswith('_description'):
                        return value

        if not data.get('__extras'):
            resource_view = get_action('resource_view_show')(
                {'ignore_auth': True},
                {'id': data['id']})
            if resource_view.get('description') is not None:
                data['description'] = resource_view['description']
            else:
                data['description'] = _get_description(resource_view)
        else:
            data['description'] = _get_description(data)

        # get research questions
        if data.get('config'):
            conf = data.get('config')
            if conf.get('__extras'):
                ext = conf.get('__extras')
                if ext.get('research_questions'):
                    data_rq = json.dumps(ext.get('research_questions'))
                    data['research_questions'] = data_rq
        else:
            if data.get('__extras'):
                ext = data.get('__extras')
                if ext.get('research_questions'):
                    data_rq = json.dumps(ext.get('research_questions'))
                    data['research_questions'] = data_rq

        # get package_id
        resource_view = get_action('resource_view_show')(
            {'ignore_auth': True},
            {'id': data['id']})
        data['package_id'] = resource_view['package_id']
        return data


mapper(Visualization, resource_view_table)
