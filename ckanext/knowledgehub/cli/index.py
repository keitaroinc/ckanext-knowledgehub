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

import click
from logging import getLogger
from ckan.lib.search import rebuild
from ckanext.knowledgehub.model import (
    Dashboard,
    ResearchQuestion,
    Theme,
    SubThemes,
    Visualization,
    Posts,
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
    'post': Posts,
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
