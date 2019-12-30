from threading import RLock
from logging import getLogger

import spacy
import en_core_web_sm as default_language_model


class NLPProcessor:

    def __init__(self, extractor=None):
        self._lock = RLock()
        self.logger = getLogger('ckanext.NLPProcessor')
        self.extractor = extractor or SpacyEntityExtractor(default_language_model)
        self._initialize()
    
    def _initialize(self):
        with self._lock:
            self.extractor.initialize()

    def extract_entities(self, text):
        return self.extractor.extract_entities(text)

    def generate_sentence(self, entities, grammar=None):
        pass


class SpacyEntityExtractor:

    def __init__(self, language_model):
        self.logger = getLogger('ckanext.SpacyEntityExtractor')
        self.lang_model = language_model
    
    def initialize(self):
        lang_model = self.lang_model
        self.logger.debug('Loading language model...')
        self.nlp = lang_model.load()
        self.logger.info('Loaded language model: %s. NLP Extractor: %s', lang_model, self.nlp)
        self.lang_model = None  # remove the reference
    
    def extract_entities(self, doc_text):
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
    
    def predict(self, inp):
        pass

    def train(self, data_set):
        pass

class ModelLocator:

    def get_model(self, name, version):
        # noop model, won't predict anything but lets the flow go through
        return MLModel() 


# Export default instances
_nlp_processor = NLPProcessor()


def get_nlp_processor():
    return _nlp_processor


model_locator = ModelLocator()