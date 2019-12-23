from datetime import datetime

from ckanext.knowledgehub.model import UserIntents, UserQuery
from ckanext.knowledgehub.lib.ml import get_nlp_processor, Worker

from logging import getLogger


class UserIntentsExtractor:

    def __init__(self, user_intents=None, nlp=None):
        self.user_intents = user_intents or UserIntents
        self.nlp = nlp or get_nlp_processor()
        self.logger = getLogger('ckanext.UserIntentsExtractor')

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
                self.logger.debug('Processed user intent for query %s for %s with result: %s', query.id, name, result)
            except Exception as e:
                ctx[name] = {
                    'error': e,
                }
                self.logger.error('Processing of user intent for query %s for %s failed with %s', query.id, name, result)

        # 3. Do post-processing and validation
        user_intent = self.post_process(ctx, user_intent)
        
        # 4. save the user intent
        self.user_intents.add_user_intent(user_intent)

        return user_intent


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

    def __init__(self,
                 extractor,
                 user_intents=None,
                 user_queries=None):
        self.extractor = extractor
        self.user_intents = user_intents or UserIntents
        self.user_queries = user_queries or UserQuery
        self.batch_size = 500
        self.logger = getLogger('ckanext.UserIntentsWorker')
    
    def _get_last(self):
        latest_intent = self.user_intents.get_latest()
        if latest_intent:
            return latest_intent.created_at
        return datetime.utcfromtimestamp(0)

    def _process_batch(self, batch, last_timestamp):
        queries = self.user_queries.get_all_after(last_timestamp, batch, self.batch_size)
        if not queries:
            return (0, last_timestamp)
        
        next_timestamp = None
        count = 0
        for query in queries:
            try:
                intent = self.process_single_query(query)
                next_timestamp = query.created_at
                count += 1
            except Exception as e:
                pass
        return (count, next_timestamp)
    
    def process_all_batches(self, last_timestamp):
        batch = 1
        while True:
            self.logger.debug('Processing batch %d starting from %s...', batch, str(last_timestamp))
            processed, last_timestamp = self._process_batch(batch, last_timestamp)
            self.logger.debug('Processed %d queries.', processed)
            if not processed:
                self.logger.debug('No more queries to process.')
                break
            batch += 1
        self.logger.debug('Processed %d batches of max size %d', batch, self.batch_size)

    def process_single_query(self, query):
        return self.extractor.extract_intents(query)

    def update_latest(self):
        self.logger.info('Extracting user intents for the latest queries...')
        last_timestamp = self._get_last()
        self.process_all_batches(last_timestamp)
        self.logger.info('Update complete.')

    def rebuild(self):
        self.logger.warning('Rebuilding user intents for all queries...')
        self.user_intents.delete_all()
        self.process_all_batches(datetime.utcfromtimestamp(0))
        self.logger.warning('Rebuild complete.')


# Default Exractor
intents_extractor = UserIntentsExtractor()

# Default worker
worker = UserIntentsWorker(intents_extractor)