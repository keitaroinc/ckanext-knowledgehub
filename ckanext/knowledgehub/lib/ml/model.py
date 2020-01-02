'''NLP and ML tools for extracting entities and model training.
'''
from threading import RLock
from logging import getLogger

import spacy
import en_core_web_sm as default_language_model


class NLPProcessor:
    '''Defines interface for extracting tagged entities from natural language
    text.

    :param extractor:`Extractor` the underlying NLP entities extractor.
        The extractor follows this interface:

            .. code-block: python

                class Extractor:

                    def initialize(self):
                        pass

                    def extract_entities(self, text):
                        pass

    '''
    def __init__(self, extractor=None):
        self._lock = RLock()
        self.logger = getLogger('ckanext.NLPProcessor')
        self.extractor = extractor or SpacyEntityExtractor(
            default_language_model)
        self._initialize()

    def _initialize(self):
        '''Performs initial startup, loading and initialization of the
        Extractor.

        This is a costly operation and must be performed only once, when the
        processor starts.
        '''
        with self._lock:
            self.extractor.initialize()

    def extract_entities(self, text):
        '''Extracts tagged entities from the given text.

        The result is a `dict` containing the `<tag>`:`<value>`.

        :param text: ``str``, the text to process and extract entites from.

        :returns: ``dict``, the result of the processing containing the
            extracted entities.
        '''
        return self.extractor.extract_entities(text)


class SpacyEntityExtractor:
    '''Entities extractor using spaCy NLP library.

    For more information on the library see https://spacy.io/

    The extractor takes a language model as its only argument. The language
    model is then used to extract and tag the text.

    SpaCy supports complex entities extraction for some pre-trained features of
    the language model. For example the default english model supports
    extraction of entities like location, time, date, currency etc.

    :param language_model: spaCy language model. This model is usually
        installed separately from the library or can be a custom trained spaCy
        model.
    '''
    def __init__(self, language_model):
        self.logger = getLogger('ckanext.SpacyEntityExtractor')
        self.lang_model = language_model

    def initialize(self):
        '''Initializes the language model.

        Once the initialization is complete, the model itself is unloaded.
        '''
        lang_model = self.lang_model
        self.logger.debug('Loading language model...')
        self.nlp = lang_model.load()
        self.logger.info('Loaded language model: %s. NLP Extractor: %s',
                         lang_model, self.nlp)
        self.lang_model = None  # remove the reference

    def extract_entities(self, doc_text):
        '''Does extraction of the pre-trained entities of the language model for
        the given text.

        The entities are labeled with the spaCy labels, like `GPE`, `LOC` for
        location, `DATE`, `TIME` for date and time etc.

        :param text: ``str``, the text to extract entities from.

        :returns: ``dict`` containing the extracted entities and a reference to
            the processed NLP document.
        '''
        doc = self.nlp(doc_text)
        entities = {}
        for token in doc.ents:
            entries = entities.get(token.label_)
            if not entries:
                entries = []
                entities[token.label_] = entries
            entries.append(token.text)
        entities['_doc'] = doc
        return entities


class MLModel:
    '''Wrapper aroung a machine learning model.

    Once loaded it offers an interface to make a prediction on custom input or
    to traing the model with new data.
    '''
    def predict(self, inp):
        '''Does a prediction on the given input.

        :param inp: ``list``/``vector``, the input to the model.

        :returns: ``list``/``vector``, the predicted values for the given
            input.
        '''
        pass

    def train(self, data_set):
        '''Performs training of the model with the training data set reference.
        '''
        pass


class ModelLocator:
    '''Manages the lookup and loading of a ML model by its name and version.
    '''
    def get_model(self, name, version):
        # noop model, won't predict anything but lets the flow go through
        return MLModel()


# Export default instances
_nlp_processor = NLPProcessor()


def get_nlp_processor():
    '''Returns the default NLP Processor.
    '''
    return _nlp_processor


# Default (NOOP) ModelLocator
model_locator = ModelLocator()
