'''User intent extraction for user queries.
'''


from datetime import datetime

from ckanext.knowledgehub.model import (
    UserIntents,
    UserQuery,
    ResearchQuestion
)
from ckanext.knowledgehub.lib.ml import (
    get_nlp_processor,
    Worker,
    model_locator as default_model_locator
)

from logging import getLogger


class UserIntentsExtractor:
    '''Extracts the user intents from the given user query.

    It uses NLP processor to extract tagged entities from the goven text and
    then tries to extract intents in three categories:
        * transactional - related to a specific research question
        * navigational - related to a specific place and date
        * informational - related to a theme/sub-theme and place and time

    :param user_intents: ``UserIntents``, user intents DAO.
    :param nlp: ``NLPProcessor``, the NLP processor to be used to extract
        entities.
    :param research_question: ``ResearchQuestion``, research question DAO.
    :param model_locator: ``ModelLocator``, the locator to load the ML model
        for text classification in a theme and sub-theme.
    '''
    def __init__(self,
                 user_intents=None,
                 nlp=None,
                 research_question=None,
                 model_locator=None):
        self.user_intents = user_intents or UserIntents
        self.research_question = research_question or ResearchQuestion
        self.model_locator = model_locator or default_model_locator
        self.nlp = nlp or get_nlp_processor()
        self.logger = getLogger('ckanext.UserIntentsExtractor')

        self.infer_chain = [
            ('transactional', self.infer_transactional),
            ('navigational', self.infer_navigational),
            ('informational', self.infer_informational),
        ]

    def extract_intents(self, query):
        '''Extracts the user intents from the given user query.

        The extraction is performed in the following manner:

            1. The query is passed through an extraction processing chain to
                extract the intents in the transactional, navigational and
                informational category.
            2. The resulting user intent is post processed to validate the
                extracted intents (if any)
            3. The resulting intent is stored in DB.

        The resulting user intent is returned as response.

        :param query: ``UserQuery``, the user query to be processed.

        :returns: ``UserIntents``, the resulting extracted user intents from
            the query.
        '''
        ctx = {}
        # 1. create new user_intent entity
        user_intent = self.user_intents()
        user_intent.user_id = query.user_id
        user_intent.user_query_id = query.id
        user_intent.primary_category = query.query_type

        # 2. pass down the inferrence chain
        for name, processor in self.infer_chain:
            result = None
            try:
                result = processor(ctx, user_intent, query)
                ctx[name] = {
                    'result': result,
                }
                self.logger.debug('Processed user intent for query %s for ' +
                                  '%s with result: %s',
                                  query.id,
                                  name,
                                  result)
            except Exception as e:
                ctx[name] = {
                    'error': e,
                }
                self.logger.error('Processing of user intent for query %s ' +
                                  'for %s failed with %s',
                                  query.id,
                                  name,
                                  e)
                self.logger.exception(e)

        # 3. Do post-processing and validation
        user_intents_extracted = self.post_process(ctx, user_intent)

        # 4. save the user intent
        if user_intents_extracted:
            self.user_intents.add_user_intent(user_intent)

        return user_intent

    def post_process(self, context, user_intent):
        '''Does post processing and validation on the extracted user intents.

        :param context: ``dict``, the processing chain context.
        :param user_intent: ``UserIntent``, the user intent model to be stored
            in DB.

        :returns: ``bool``, `True` if some user intents have been extracted,
            otherwise `False`.
        '''
        if any([user_intent.inferred_transactional,
               user_intent.inferred_navigational,
               user_intent.inferred_informational]):
            return True
        return False

    def infer_transactional(self, context, user_intent, query):
        '''Tries to infer the transactional intent of the user.

        This is part of the processing chain.

        :param context: ``dict``, the processing chain context.
        :param user_intent: ``UserIntent``, the user intent model that is not
            yet stored in the DB and should be populated with the intent.
        :param query: ``UserQuery``, the user query from which the intent is
            being extracted from.

        :returns: ``dict``, the result of the extraction, optionally containing
            the user intent or an error.
        '''
        # 1. Try the search with Solr
        #    - if found, extract research question + theme + sub theme
        # 2. If not found Try to classify the query in theme/sub-theme
        # 3. Populate the context and user_intent
        research_question, theme, sub_theme = self._extract_research_question(
            query.query_text)
        if research_question:
            user_intent.research_question = research_question['id']
            user_intent.inferred_transactional = research_question['title']

        prediction = False
        if not theme or not sub_theme:
            pred_theme, pred_sub_theme = self._classify_query(query.query_text)
            theme = theme or pred_theme
            sub_theme = sub_theme or pred_sub_theme
            prediction = True

        user_intent.theme = theme
        user_intent.sub_theme = sub_theme

        return {
            'research_question': research_question,
            'theme': theme,
            'theme_value': (research_question or {}).get('theme_title'),
            'sub_theme': sub_theme,
            'sub_theme_value': (research_question or {}).get(
                'sub_theme_title'),
            'predicted_values': prediction,
        }

    def _extract_research_question(self, query_text):
        results = self.research_question.search_index(q='text:' + query_text,
                                                      rows=1)
        if results.hits:
            rq = results.docs[0]
            return (rq, rq.get('theme_id'), rq.get('sub_theme_id'))
        return (None, None, None)

    def _classify_query(self, query_text):
        # classify in theme first
        theme = self.model_locator.get_model('theme_classifier',
                                             'latest').predict(query_text)
        sub_theme = self.model_locator.get_model('sub_theme_classifier',
                                                 'latest').predict(query_text)
        return (theme, sub_theme)

    def infer_navigational(self, context, user_intent, query):
        '''Tries to infer the navigational intent of the user.

        This is part of the processing chain.

        :param context: ``dict``, the processing chain context.
        :param user_intent: ``UserIntent``, the user intent model that is not
            yet stored in the DB and should be populated with the intent.
        :param query: ``UserQuery``, the user query from which the intent is
            being extracted from.

        :returns: ``dict``, the result of the extraction, optionally containing
            the user intent or an error.
        '''
        # 1. Extract LOCATION and DATE/TIME entities
        # 2. If theme/sub-theme not already inffered, try infering from NOUNS
        # 3. Populate theme/sub-theme + LOCATION + DATE
        entities = self.nlp.extract_entities(query.query_text)
        inffered = context.get('transactional', {}).get('result', {})
        theme = inffered.get('theme_value')
        sub_theme = inffered.get('sub_theme_value')
        ent_location = self._extract_entity(entities, ['LOC', 'GPE'])
        ent_date = self._extract_entity(entities, ['DATE', 'TIME'])

        if not theme and not sub_theme:
            theme, sub_theme = self._infer_themes_from_entities(entities)
        nav_text = ''
        if theme or sub_theme:
            nav_text += (theme or sub_theme) + ' '
        if ent_location:
            nav_text += ent_location + ' '
        if ent_date:
            nav_text += ent_date

        if not user_intent.theme and theme:
            user_intent.theme = theme
        if not user_intent.sub_theme:
            user_intent.sub_theme = sub_theme

        user_intent.inferred_navigational = nav_text

        return {
            'nlp_entities': entities,
            'theme': theme,
            'sub_theme': sub_theme,
            'location': ent_location,
            'date': ent_date,
            'inferred': nav_text,
        }

    def _extract_entity(self, entities, types):
        ents = []

        for tp in types:
            if entities.get(tp):
                value = entities[tp]
                if isinstance(value, list):
                    ents += value
                else:
                    ents.append(value)
        if ents:
            return ents[0]
        return None

    def _infer_themes_from_entities(self, entities):
        return (None, None)

    def infer_informational(self, context, user_intent, query):
        '''Tries to infer the informational intent of the user.

        This is part of the processing chain.

        :param context: ``dict``, the processing chain context.
        :param user_intent: ``UserIntent``, the user intent model that is not
            yet stored in the DB and should be populated with the intent.
        :param query: ``UserQuery``, the user query from which the intent is
            being extracted from.

        :returns: ``dict``, the result of the extraction, optionally containing
            the user intent or an error.
        '''
        entities = (context.get('navigational', {})
                    .get('nlp_entities')
                    or self.nlp.extract_entities(query.query_text))
        inffered = context.get('transactional', {}).get('result', {})
        theme = inffered.get('theme_value')
        sub_theme = inffered.get('sub_theme_value')

        location = self._extract_entity(entities, ['LOC', 'GPE'])
        date = self._extract_entity(entities, ['DATE', 'TIME'])

        themes = []
        for t in [theme, sub_theme]:
            if t:
                themes.append(t)

        if not themes or not (location or date):
            return {
                'message': 'Unable to extract informational context',
            }

        inferred_informational = ''
        for p_theme in themes:
            inf_text = p_theme
            if location:
                inf_text += ' ' + 'in' + ' ' + location
            if date:
                inf_text += ' ' + 'at' + ' ' + date
            if inferred_informational:
                inferred_informational += ', '
            inferred_informational += inf_text

        user_intent.inferred_informational = inferred_informational

        return {
            'inferred': inferred_informational,
        }


class UserIntentsWorker:
    '''A ``Worker`` that processes the ``UserQuery`` entries and extracts the
    user intents for each using the ``UserIntentsExtractor``.

    :param extractor: ``UserIntentsExtractor``, the instance of the extractor
        to be used to extract the intents with for each unprocessed query.
    :param user_intents: ``UserIntents``, user intents DAO.
    :param user_queries: ``UserQuery``, user queries DAO.
    '''
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
        queries = self.user_queries.get_all_after(last_timestamp,
                                                  batch,
                                                  self.batch_size)
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
                self.logger.warning('Error in processing: %s', e)
                self.logger.exception(e)

        return (count, next_timestamp)

    def process_all_batches(self, last_timestamp):
        '''Processes the user queries that are not yet processed after the
        given timestamp.

        The processing is done in batches - a batch of queries is extracted
        from the DB, then each query is processed to extract the user intents.
        The process completes when all queries after the timestamp are
        processed.

        :param last_timestamp: ``datetime.datetime``, process all queries after
            this time.
        '''
        batch = 1
        while True:
            self.logger.debug('Processing batch %d starting from %s...',
                              batch,
                              str(last_timestamp))
            processed, last_timestamp = self._process_batch(batch,
                                                            last_timestamp)
            self.logger.debug('Processed %d queries.', processed)
            if not processed:
                self.logger.debug('No more queries to process.')
                break
            batch += 1
        self.logger.debug('Processed %d batches of max size %d',
                          batch,
                          self.batch_size)

    def process_single_query(self, query):
        '''Processes a single UserQuery.

        :param query: ``UserQuery``, the query to be processed with the
            extractor.

        :returns: ``UserIntent``, the extracted user intents.
        '''
        return self.extractor.extract_intents(query)

    def update_latest(self):
        '''Updates the user intents by processing the queries that are not yet
        processed.

        The processing is incremental in the sense that not all queries are
        processed from scratch, but only the intents fro the latest unprocessed
        queries are extracted and stored in the database.
        '''
        self.logger.info('Extracting user intents for the latest queries...')
        last_timestamp = self._get_last()
        self.process_all_batches(last_timestamp)
        self.logger.info('Update complete.')

    def rebuild(self):
        '''Performs a full rebuild of the user intents.

        First all existing user intents are deleted, the all collected user
        queries are processed and intents are extracted.
        '''
        self.logger.warning('Rebuilding user intents for all queries...')
        self.user_intents.delete_all()
        self.process_all_batches(datetime.utcfromtimestamp(0))
        self.logger.warning('Rebuild complete.')


# Default Exractor
intents_extractor = UserIntentsExtractor()

# Default worker
worker = UserIntentsWorker(intents_extractor)
