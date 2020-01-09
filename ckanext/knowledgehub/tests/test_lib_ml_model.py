from mock import Mock, patch, MagicMock

from ckan.tests import helpers

from ckanext.knowledgehub.lib.ml.model import (
    NLPProcessor,
    SpacyEntityExtractor,
    ModelLocator,
)

from nose.tools import (
    assert_true,
    assert_equals,
    raises,
)

class TestNLPProcessor(helpers.FunctionalTestBase):

    
    def test_extract_entities(self):
        extractor = MagicMock()
        processor = NLPProcessor(extractor=extractor)

        extractor.extract_entities.return_value = {
            'GPE': ['Syria'],
            'DATE': ['2019'],
        }

        entities = processor.extract_entities(u'Refugees in Syria in 2019')
        assert_true(entities is not None)
        assert_true(entities.get('GPE') is not None)
        assert_equals(entities['GPE'][0], 'Syria')
        assert_true(entities.get('DATE') is not None)
        assert_equals(entities['DATE'][0], '2019')

        extractor.extract_entities.assert_called_once_with(u'Refugees in Syria in 2019')
        extractor.initialize.assert_called_once()


class TestSpacyEntityExtractor(helpers.FunctionalTestBase):

    def test_initialize(self):
        import en_core_web_sm as language_model
        extractor = SpacyEntityExtractor(language_model)
        extractor.initialize()

        assert_true(extractor.nlp is not None)
    
    def test_extract_entities(self):
        import en_core_web_sm as language_model
        extractor = SpacyEntityExtractor(language_model)
        
        extractor.initialize()

        entities = extractor.extract_entities(u'Refugees in Syria in 2019')
        assert_true(entities is not None)
        assert_true(entities.get('GPE') is not None)
        assert_equals(entities['GPE'][0], 'Syria')
        assert_true(entities.get('DATE') is not None)
        assert_equals(entities['DATE'][0], '2019')


class TestMLModels(helpers.FunctionalTestBase):

    def test_ml_model_locator(self):
        locator = ModelLocator()
        model = locator.get_model('test', '0.1.1')
        assert_true(model is not None)