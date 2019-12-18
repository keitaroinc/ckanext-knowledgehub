from ckanext.knowledgehub.model import UserIntents
from ckanext.knowledgehub.lib.ml import get_nlp_processor

from logging import getLogger


logger = getLogger(__name__)


class UserIntentsExtractor:

    def __init__(self, user_intents=None, nlp=None):
        self.user_intents = user_intents or UserIntents
        self.nlp = nlp or get_nlp_processor()

        self.infer_chain = [
            ('transactional', self.infer_transactional),
            ('navigational', self.infer_navigational),
            ('informational', self.infer_informational),
        ]

    def extract_intents(self, query):
        ctx = {}
        # 1. create new user_intent entity
        user_intent = self.user_intents()

        # 2. pass down the inferrence chain
        for name, processor in self.infer_chain:
            try:
                result = processor(ctx, user_intent, query)
                ctx[name] = {
                    'result': result,
                }
                logger.debug('Processed user intent for query %s for %s with result: %s', query.id, name, result)
            except Exception as e:
                ctx[name] = {
                    'error': e,
                }
                logger.error('Processing of user intent for query %s for %s failed with %s', query.id, name, result)

        # 3. Do post-processing and validation
        user_intent = self.post_process(ctx, user_intent)
        
        # 4. save the user intent
        self.user_intents.add_user_intent(user_intent)


    def post_process(self, context, user_intent):
        # TODO: check what have we inferred and errors.
        return user_intent

    def infer_transactional(self, context, user_intent, query):
        pass

    def infer_navigational(self, context, user_intent, query):
        pass

    def infer_informational(self, context, user_intent, query):
        pass


class UserIntentsWorker:

    def __init__(self, extractor):
        self.extractor = extractor
    
    def update_latest(self):
        pass

    def rebuild(self):
        pass