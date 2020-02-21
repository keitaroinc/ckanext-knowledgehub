import ckan.plugins.toolkit as toolkit


class DataManager:
    ''' Manage the training data'''

    @staticmethod
    def create_corpus(corpus):
        ''' Store the machine learning corpus

        :param corpus: the machine learning corpus
        :type corpus: string

        :returns: the stored corpus
        :rtype: dict
        '''
        return toolkit.get_action('corpus_create')(
            {'ignore_auth': True},
            {'corpus': corpus}
        )

    @staticmethod
    def get_corpus():
        ''' Get the data in knowledgehub and create corpus

        :returns: the machine learning corpus
        :rtype: string
        '''
        kwh_data = toolkit.get_action(
            'kwh_data_list')({'ignore_auth': True}, {})

        corpus = ''
        if kwh_data.get('total'):
            data = kwh_data.get('data', [])
            for entry in data:
                corpus += ' %s' % entry.get('title')
                if entry.get('description'):
                    corpus += ' %s' % entry.get('description')

        return corpus

    @staticmethod
    def get_last_corpus():
        ''' Return the corpus usd in the last training of the model '''

        return toolkit.get_action('get_last_rnn_corpus')(
            {'ignore_auth': True}, {})

    @staticmethod
    def prepare_corpus(corpus):
        ''' Find the unique chars in the corpus and index the characters '''

        unique_chars = sorted(list(set(corpus)))
        char_indices = dict((c, i) for i, c in enumerate(unique_chars))
        indices_char = dict((i, c) for i, c in enumerate(unique_chars))

        return (unique_chars, char_indices, indices_char)
