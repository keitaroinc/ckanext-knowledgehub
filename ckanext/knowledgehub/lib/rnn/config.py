import os
import time
import logging

from ckan.common import config


class PredictiveSearchConfig(object):
    def __init__(self):
        self.corpus_length = int(config.get(
            u'ckanext.knowledgehub.rnn.min_length_corpus', 500))
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
