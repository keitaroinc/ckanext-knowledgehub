''' Contains overrides for CKAN search index functionality to support multiple
entity types: package, dashboard, visualization etc.
'''

from ckan.lib.search.query import PackageSearchQuery
from ckan.lib.search.common import make_connection, SearchError
from ckan.common import config
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
    log.info('CKAN core queries has been patched successfully.')
