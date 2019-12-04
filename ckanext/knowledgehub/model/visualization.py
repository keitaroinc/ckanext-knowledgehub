from ckan.model import ResourceView, resource_view_table
from ckan.model.meta import mapper

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


mapper(Visualization, resource_view_table)
