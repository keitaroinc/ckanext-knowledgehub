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

from mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from collections import namedtuple

from ckan.tests import helpers
from pysolr import Results

from ckanext.knowledgehub.lib.intents import (
    UserIntentsExtractor,
    UserIntentsWorker,
)

from ckanext.knowledgehub.model import (
    UserIntents,
    ResearchQuestion,
    UserQuery,
)

from nose.tools import (
    assert_true,
    assert_equals,
    raises,
)


class TestUserIntentsExtractor:


    def test_infer_transactional(self):
        user_intents = MagicMock()
        nlp = MagicMock()
        research_question = MagicMock()
        model_locator = MagicMock()

        rq = {
            'id': 'question-id',
            'theme_id': 'theme-id',
            'theme_title': 'Theme',
            'sub_theme_id': 'sub-theme-id',
            'sub_theme_title': 'SubTheme',
            'title': 'RQ Title',
        }
        research_question.search_index.return_value = Results({
            'response': {
                'docs': [rq],
                'numFound': 1,
            }
        })

        extractor = UserIntentsExtractor(user_intents, nlp, research_question, model_locator)

        context = {}
        user_intent = UserIntents()
        query = UserQuery(id='query-id',
                          user_id='user-1',
                          query_type='package_search',
                          query_text='Some text')

        result = extractor.infer_transactional(context, user_intent, query)
        assert_true(result is not None)
        assert_equals(result.get('research_question'), rq)
        assert_equals(result.get('theme'), 'theme-id')
        assert_equals(result.get('theme_value'), 'Theme')
        assert_equals(result.get('sub_theme'), 'sub-theme-id')
        assert_equals(result.get('sub_theme_value'), 'SubTheme')
        assert_equals(result.get('predicted_values'), False)
    
    def test_infer_navigational(self):
        user_intents = MagicMock()
        nlp = MagicMock()

        nlp.extract_entities.return_value = {
            'GPE': ['Syria'],
            'DATE': ['2019'],
        }

        research_question = MagicMock()
        model_locator = MagicMock()

        rq = {
            'id': 'question-id',
            'theme_id': 'theme-id',
            'theme_title': 'Theme',
            'sub_theme_id': 'sub-theme-id',
            'sub_theme_title': 'SubTheme',
            'title': 'RQ Title',
        }
        research_question.search_index.return_value = Results({
            'response': {
                'docs': [rq],
                'numFound': 1,
            }
        })


        extractor = UserIntentsExtractor(user_intents, nlp, research_question, model_locator)

        context = {
            'transactional': {
                'result': {
                    'theme_value': 'Theme',
                    'sub_theme_value': 'SubTheme',
                }
            }
        }
        user_intent = UserIntents()
        query = UserQuery(id='query-id',
                          user_id='user-1',
                          query_type='package_search',
                          query_text='Some text')

        result = extractor.infer_navigational(context, user_intent, query)
        assert_true(result is not None)
        assert_equals(result.get('inferred'), 'Theme Syria 2019')

    def test_infer_informational(self):
        user_intents = MagicMock()
        nlp = MagicMock()

        nlp.extract_entities.return_value = {
            'GPE': ['Syria'],
            'DATE': ['2019'],
        }

        research_question = MagicMock()
        model_locator = MagicMock()

        rq = {
            'id': 'question-id',
            'theme_id': 'theme-id',
            'theme_title': 'Theme',
            'sub_theme_id': 'sub-theme-id',
            'sub_theme_title': 'SubTheme',
            'title': 'RQ Title',
        }
        research_question.search_index.return_value = [rq]


        extractor = UserIntentsExtractor(user_intents, nlp, research_question, model_locator)

        context = {
            'transactional': {
                'result': {
                    'theme_value': 'Theme',
                    'sub_theme_value': 'SubTheme',
                }
            }
        }
        user_intent = UserIntents()
        query = UserQuery(id='query-id',
                          user_id='user-1',
                          query_type='package_search',
                          query_text='Some text')

        result = extractor.infer_informational(context, user_intent, query)

        assert_true(result is not None)
        assert_equals(result.get('inferred'), 'Theme in Syria at 2019, SubTheme in Syria at 2019')
    
    def test_extract_intents(self):
        user_intents = MagicMock()
        nlp = MagicMock()

        research_question = MagicMock()
        model_locator = MagicMock()

        extractor = UserIntentsExtractor(user_intents, nlp, research_question, model_locator)

        extractor.post_process = Mock()
        extractor.post_process.return_value = True

        query = UserQuery(id='query-id',
                          user_id='user-1',
                          query_type='package_search',
                          query_text='Some text')

        result = extractor.extract_intents(query)

        assert_true(result is not None)
        assert_true(result.get('transactional') is not None)
        assert_true(result.get('informational') is not None)
        assert_true(result.get('navigational') is not None)
        
        user_intents.assert_called_once()
        user_intents.add_user_intent.assert_called_once
        extractor.post_process.assert_called_once()


class TestUserIntentsWorker:
    
    def test_process_all_batches(self):
        extractor = MagicMock()
        user_intents = MagicMock()
        user_queries = MagicMock()
        last_timestamp = datetime.now()

        Query = namedtuple('QueryMock', ['id', 'created_at'])

        def get_all_after_mock(ts, batch, batch_size):
            assert_equals(batch_size, 500)
            assert_true(ts is not None)
            if batch == 3:
                return []
            return [Query('query-' + str(i), ts + timedelta(seconds=i+1)) for i in range(0, batch_size)]

        user_queries.get_all_after.side_effect = get_all_after_mock

        worker = UserIntentsWorker(extractor, user_intents, user_queries)

        worker.process_single_query = Mock()

        worker.process_all_batches(last_timestamp)

        assert_equals(worker.process_single_query.call_count, 1000)
        assert_equals(user_queries.get_all_after.call_count, 3)
    
    def test_update_latest(self):
        extractor = MagicMock()
        user_intents = MagicMock()
        user_queries = MagicMock()
        UserIntent = namedtuple('UserIntentMock', ['id', 'created_at'])

        last_timestamp = datetime.now()

        user_intents.get_latest.return_value = UserIntent('000', last_timestamp)

        worker = UserIntentsWorker(extractor, user_intents, user_queries)
        worker.process_all_batches = Mock()

        worker.update_latest()

        worker.process_all_batches.assert_called_once_with(last_timestamp)
        user_intents.get_latest.assert_called_once()

    def test_rebuild(self):
        extractor = MagicMock()
        user_intents = MagicMock()
        user_queries = MagicMock()

        last_timestamp = datetime.utcfromtimestamp(0)


        worker = UserIntentsWorker(extractor, user_intents, user_queries)
        worker.process_all_batches = Mock()

        worker.rebuild()

        worker.process_all_batches.assert_called_once_with(last_timestamp)