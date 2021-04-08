"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

''' Contains overrides for CKAN search index functionality to support multiple
entity types: package, dashboard, visualization etc.
'''

from ckan.lib.search.query import PackageSearchQuery, VALID_SOLR_PARAMETERS
from ckan.lib.search.common import make_connection, SearchError
from ckan.common import config

from ckanext.knowledgehub.lib.profile import user_profile_service
from ckanext.knowledgehub.lib.solr import boost_solr_params

import pysolr
import logging

log = logging.getLogger(__name__)


class KnowledgeHubPackageSearchQuery(PackageSearchQuery):

    def get_index(self, reference):
        query = {
            'rows': 1,
            'q': 'name:"%s" OR id:"%s"' % (reference, reference),
            'wt': 'json',
            'fq': [
                    'site_id:"%s"' % config.get('ckan.site_id'),
                    'entity_type:package'
            ],
        }

        try:
            if query['q'].startswith('{!'):
                raise SearchError('Local parameters are not supported.')
        except KeyError:
            pass

        conn = make_connection(decode_dates=False)
        log.debug('Package query: %r' % query)
        try:
            solr_response = conn.search(**query)
        except pysolr.SolrError as e:
            raise SearchError('SOLR returned an error running '
                              'query: %r Error: %r' %
                              (query, e))

        if solr_response.hits == 0:
            raise SearchError('Dataset not found in '
                              'the search index: %s' % reference)
        else:
            return solr_response.docs[0]
    
    def run(self, query, permission_labels=None, **kwargs):
        user_id = query.get('boost_for')
        if user_id:
            query.pop('boost_for')

        boost_params = user_profile_service.get_interests_boost(user_id)
        if boost_params:
            query.update(boost_solr_params(boost_params))

        return super(KnowledgeHubPackageSearchQuery, self).run(
            query,
            permission_labels,
            **kwargs
        )

def patch_ckan_core_search():
    '''Patches CKAN's core search funtionality to add fq='entity_type:package'
    when searching for packages in Solr.
    With KnowledgeHub extension, Solr is extended to support multiple types of
    entities for indexing, so we must take into account the entity_type when
    doing index searches.
    '''
    import ckan.lib.search as ckan_search
    if not hasattr(ckan_search, '_QUERIES'):
        raise Exception('Cannot patch CKAN query search: Unable to register '
                        'custom PackageSearchQuery to CKAN search query '
                        'mechanism. The _QUERIES global in ckan.lib.search '
                        'was not found, which means that this patch will not'
                        'work on your curren CKAN version.')

    ckan_search._QUERIES['package'] = KnowledgeHubPackageSearchQuery

    # Add 'bq' for edismax boost query
    VALID_SOLR_PARAMETERS.add('bq')

    log.info('CKAN core queries has been patched successfully.')
