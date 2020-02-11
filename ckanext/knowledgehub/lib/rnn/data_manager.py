import ckan.plugins.toolkit as toolkit


class DataManager:
    @staticmethod
    def create_corpus(corpus):
        return toolkit.get_action('corpus_create')(
            {'ignore_auth': True},
            {'corpus': corpus}
        )

    @staticmethod
    def get_corpus():
        kwh_data = toolkit.get_action(
            'kwh_data_list')({'ignore_auth': True}, {})

        corpus = ''
        if kwh_data.get('total'):
            data = kwh_data.get('data', [])
            for entry in data:
                corpus += ' %s' % entry.get('content')

        return corpus

    @staticmethod
    def get_last_corpus():
        return toolkit.get_action('get_last_rnn_corpus')(
            {'ignore_auth': True}, {})

    @staticmethod
    def prepare_corpus(corpus):
        unique_chars = sorted(list(set(corpus)))
        char_indices = dict((c, i) for i, c in enumerate(unique_chars))
        indices_char = dict((i, c) for i, c in enumerate(unique_chars))

        return (unique_chars, char_indices, indices_char)
