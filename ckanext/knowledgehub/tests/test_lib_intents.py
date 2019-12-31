from mock import Mock, patch, MagicMock

from ckan.tests import helpers

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
        research_question.search_index.return_value = [rq]


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
    pass