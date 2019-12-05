from ckan.model import ResourceView, resource_view_table
from ckan.model.meta import mapper
from ckan.logic import get_action

from ckanext.knowledgehub.lib.solr import Indexed, mapped


class Visualization(ResourceView, Indexed):

    indexed = [
        mapped('id', 'entity_id'),
        'resource_id',
        'title',
        'description',
        'view_type',
    ]

    doctype = 'visualization'

    @staticmethod
    def before_index(data):
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
        return data


mapper(Visualization, resource_view_table)
