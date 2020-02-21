import logging
import os

import heapq
import numpy as np
import tensorflow as tf
from keras.models import load_model, model_from_json
from filelock import FileLock

from ckanext.knowledgehub.lib.rnn.data_manager import DataManager
from ckanext.knowledgehub.lib.rnn.config import PredictiveSearchConfig


class PredictiveSearchModel(PredictiveSearchConfig):
    ''' Use the machine learning model trained by the worker.

    Has ability to predict the next characters or word for given text.
    '''

    def __init__(self):
        super(PredictiveSearchModel, self).__init__()
        self.model = None
        self.unique_chars = None
        self.char_indices = None
        self.indices_char = None
        self.logger = logging.getLogger('ckanext.PredictiveSearchModel')

    def prepare_input(self, text):
        x = np.zeros((1, self.sequence_length, len(self.unique_chars)))
        for t, char in enumerate(text):
            x[0, t, self.char_indices[char]] = 1.

        return x

    def sample(self, preds, top_n=3):
        preds = np.asarray(preds).astype('float64')
        preds = np.log(preds)
        exp_preds = np.exp(preds)
        preds = exp_preds / np.sum(exp_preds)

        return heapq.nlargest(top_n, range(len(preds)), preds.take)

    def predict_completion(self, text):
        completion = ''
        while True:
            x = self.prepare_input(text)
            preds = self.model.predict(x, verbose=0)[0]
            next_index = self.sample(preds, top_n=1)[0]
            next_char = self.indices_char[next_index]
            if not next_char.isalnum():
                return completion

            text = text[1:] + next_char

            completion += next_char
            if (len(text + completion) + 2 > len(text) and next_char == ' '):
                return completion

    def predict(self, search_text):
        self.unique_chars, self.char_indices, self.indices_char = \
            DataManager.prepare_corpus(DataManager.get_last_corpus())

        text = search_text[-self.sequence_length:].lower()
        unique_chars_text = sorted(list(set(text)))
        for char in unique_chars_text:
            if char not in self.unique_chars:
                return []

        if self.sequence_length > len(text):
            return []

        if not os.path.isfile(self.weights_path):
            self.logger.debug(
                'Model weights %s does not exist!' % self.weights_path)
            return []
        if not os.path.isfile(self.network_path):
            self.logger.debug(
                'Model network does not exist!' % self.network_path)
            return []

        try:
            lock_model_network = FileLock('%s.lock' % self.weights_path)
            lock_model_weigths = FileLock('%s.lock' % self.network_path)

            with lock_model_network.acquire(timeout=1000):
                with lock_model_weigths.acquire(timeout=1000):
                    graph = tf.Graph()
                    with graph.as_default():
                        session = tf.Session()
                        with session.as_default():
                            with open(self.network_path, 'r') as json_file:
                                loaded_model_json = json_file.read()

                            self.model = model_from_json(loaded_model_json)
                            self.model.load_weights(self.weights_path)

                            x = self.prepare_input(text)
                            preds = self.model.predict(x, verbose=0)[0]
                            next_indices = self.sample(
                                preds, self.number_predictions)

                            return [
                                self.indices_char[idx] +
                                self.predict_completion(
                                    text[1:] + self.indices_char[idx]
                                ) for idx in next_indices]
        except Exception as e:
            self.logger.debug('Error while prediction: %s' % str(e))
            return []
