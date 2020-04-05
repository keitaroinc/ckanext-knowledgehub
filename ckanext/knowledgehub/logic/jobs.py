import ckan.lib.jobs as jobs
from ckan.plugins import toolkit
from ckan.lib.search import rebuild as ckan_index_rebuild
from ckanext.knowledgehub.lib.quality import (
    Accuracy,
    Completeness,
    Consistency,
    DataQualityMetrics,
    Timeliness,
    Uniqueness,
    Validity,
)
from ckanext.knowledgehub.model import (
    Dashboard,
    ResearchQuestion,
    Visualization,
)
from ckanext.knowledgehub.lib.solr import escape_str, Indexed, unprefixed
from ckanext.knowledgehub.lib.email import send_notification_email
from ckanext.knowledgehub.helpers import get_members

from logging import getLogger


logger = getLogger(__name__)


def calculate_metrics(package_id):
    metrics = DataQualityMetrics(metrics=[
        Accuracy(),
        Completeness(),
        Consistency(),
        Timeliness(),
        Uniqueness(),
        Validity()
    ])

    metrics.calculate_metrics_for_dataset(package_id)


def schedule_data_quality_check(package_id):
    jobs.enqueue(calculate_metrics, [package_id])


class IndexRefresh(object):

    def find_documents(self, query):
        pass

    def refresh_index(self, id):
        pass


class IndexedModelsRefreshIndex(IndexRefresh):

    def __init__(self, model, getfn='get'):
        self.model = model
        self.getfn = getfn
        self.logger = getLogger('ckanext.jobs.IndexedModelsRefreshIndex[%s]' %
                                self.model)

    def find_documents(self, query):
        doc_ids = []
        for doc in self.model.search_index(q='text:%s' % escape_str(query)):
            if doc.get('id'):
                doc_ids.append(doc['id'])
        self.logger.debug('Lookup for query "%s" found %d documents',
                          query,
                          len(doc_ids))
        return doc_ids

    def refresh_index_for(self, id):
        doc = getattr(self.model, self.getfn)(id)
        if doc:
            doc = doc.__dict__
            self.logger.debug('Updating doc: %s', str(doc))
            return self.model.update_index_doc(doc)
        self.logger.debug('Document with id %s was not found.', id)

    def refresh_index(self, query):
        for id in self.find_documents(query):
            try:
                self.refresh_index_for(id)
            except Exception as e:
                self.logger.warning('Failed to refresh index for %s. '
                                    'Error: %s', id, str(e))
                self.logger.exception(e)

    def __str__(self):
        return 'IndexedModelsRefreshIndex<%s>' % str(self.model)

    def __repr__(self):
        return self.__str__()


class _IndexedPackage(Indexed):
    doctype = 'package'
    indexed = [unprefixed('id')]


class DatasetIndexRefresh(IndexedModelsRefreshIndex):

    def __init__(self):
        super(DatasetIndexRefresh, self).__init__(_IndexedPackage)

    def refresh_index(self, query):
        package_ids = self.find_documents(query)

        self.logger.debug('Rebuilding index for packages: %s', package_ids)
        if package_ids:
            for package_id in package_ids:
                ckan_index_rebuild(package_id=package_id)


def update_index(query):
    refresh_indexers = [
        IndexedModelsRefreshIndex(Dashboard),
        IndexedModelsRefreshIndex(Visualization),
        IndexedModelsRefreshIndex(ResearchQuestion, getfn='get_by_id'),
        DatasetIndexRefresh(),
    ]

    for indexer in refresh_indexers:
        try:
            logger.debug('Refreshing index using indexer: %s', indexer)
            indexer.refresh_index(query)
        except Exception as e:
            logger.warning('Failed to refresh index for query: %s. '
                           'Error: %s', query, str(e))
            logger.exception(e)


class _DatasetRelatedDashboardsRefresh(IndexedModelsRefreshIndex):

    def __init__(self):
        super(_DatasetRelatedDashboardsRefresh, self).__init__(Dashboard)

    def find_documents(self, query):
        doc_ids = []
        for doc in self.model.search_index(**query):
            if doc.get('id'):
                doc_ids.append(doc['id'])
        self.logger.debug('Lookup for query "%s" found %d documents',
                          query,
                          len(doc_ids))
        return doc_ids


def update_dashboard_index(datasets):
    if not datasets:
        logger.debug('No datasets ids to refresh dashboards for.')
        return
    index_refresh = _DatasetRelatedDashboardsRefresh()
    query = {
        'q': 'text:*',
        'fq': [
            ' OR '.join(['idx_datasets:"%s"' % _id for _id in datasets])
        ]
    }
    index_refresh.refresh_index(query)


def schedule_update_index(query):
    jobs.enqueue(update_index, [query])


def schedule_notification_email(recipient, template, data):
    jobs.enqueue(send_notification_email, [recipient, template, data])


def schedule_broadcast_notification_email(group, template, data):
    group_members = [user_id for user_id, _, _ in get_members({
        'ignore_auth': True,
    }, group)]
    for recipient in group_members:
        schedule_notification_email(recipient, template, data)
