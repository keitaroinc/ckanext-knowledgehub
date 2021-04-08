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
