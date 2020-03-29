import click
from logging import getLogger
from ckan.lib.search import rebuild
from ckanext.knowledgehub.model import (
    Dashboard,
    ResearchQuestion,
    Theme,
    SubThemes,
    Visualization,
)

logger = getLogger(__name__)


def _mock_translator():
    # Workaround until the core translation function defaults to the Flask one
    from paste.registry import Registry
    from ckan.lib.cli import MockTranslator
    registry = Registry()
    registry.prepare()
    from pylons import translator
    registry.register(translator, MockTranslator())


class CkanCoreIndex:

    def rebuild_index(self):
        rebuild()


INDEX_EXECUTORS = {
    'dashboard': Dashboard,
    'research-question': ResearchQuestion,
    'visualization': Visualization,
    'ckan': CkanCoreIndex(),
}


@click.group(u'search-index')
def index():
    pass


def rebuild_index_for(doctype):
    executor = INDEX_EXECUTORS.get(doctype)
    if not executor:
        raise Exception('Invalid doctype \'{}\'. ' +
                        'Available index document types: {}',
                        doctype,
                        ', '.join(
                            sorted([k for k, _ in INDEX_EXECUTORS.items()])))
    logger.info('Rebuilding index for: %s', doctype)
    executor.rebuild_index()


@index.command('rebuild', short_help='Rebuild the search index')
@click.option('--model',
              default='all',
              help='Rebuild index for specified model type. Available are: ' +
                   ','.join(sorted([k for k, _ in INDEX_EXECUTORS.items()])))
def rebuild_index(model):
    _mock_translator()
    types = [model]
    if model == 'all':
        # TODO: Add CKAN search index rebuild here.
        types = sorted([k for k, _ in INDEX_EXECUTORS.items()])
        logger.info('Rebuilding search index for all models: %s', types)

    for doctype in types:
        rebuild_index_for(doctype)
