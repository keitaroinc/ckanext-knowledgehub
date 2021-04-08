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

import os
import time

from ckan.common import config


class PredictiveSearchConfig(object):
    ''' Hold the configuration for the machine learning model and worker '''

    def __init__(self):
        self.corpus_length = int(config.get(
            u'ckanext.knowledgehub.rnn.min_length_corpus', 10000))
        self.sequence_length = config.get(
            u'ckanext.knowledgehub.rnn.sequence_length', 10)
        self.step = int(
            config.get(u'ckanext.knowledgehub.rnn.sentence_step', 1))
        self.epochs = int(
            config.get(u'ckanext.knowledgehub.rnn.max_epochs', 50))
        self.weights_path = config.get(
            u'ckanext.knowledgehub.rnn.model_weights',
            './keras_model_weights.h5'
        )
        self.network_path = config.get(
            u'ckanext.knowledgehub.rnn.model_network',
            './keras_model_network.h5'
        )
        self.history_path = config.get(
            u'ckanext.knowledgehub.rnn.history',
            './history.p'
        )
        self.temp_weigths_path = os.path.join(
            os.path.dirname(self.weights_path),
            'keras_model_%s.h5' % time.time()
        )
        self.number_predictions = int(
            config.get(
                u'ckanext.knowledgehub.rnn.number_predictions',
                3
            )
        )
