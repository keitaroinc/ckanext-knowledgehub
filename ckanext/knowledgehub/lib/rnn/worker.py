import logging
import os
import pickle
import time

import numpy as np
import tensorflow as tf
from filelock import FileLock

from keras.models import Sequential, load_model
from keras.layers import Dense, Activation
from keras.layers import LSTM, Dropout
from keras.layers.core import Dense, Activation, Dropout, RepeatVector
from keras.optimizers import RMSprop
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

from ckan.common import config
import ckan.plugins.toolkit as toolkit

np.random.seed(42)
tf.set_random_seed(42)


class DataManager:
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
    def prepare_corpus(corpus):
        unique_chars = sorted(list(set(corpus)))
        char_indices = dict((c, i) for i, c in enumerate(unique_chars))
        indices_char = dict((i, c) for i, c in enumerate(unique_chars))

        return (unique_chars, char_indices, indices_char)


class PredictiveSearchWorker:
    def __init__(self):
        self.model = Sequential()
        self.history = None
        self.corpus = None
        self.data = None
        self.unique_chars = None
        self.char_indices = None
        self.x = None
        self.y = None
        self.logger = logging.getLogger(__name__)
        self.corpus_length = int(config.get(
            u'ckanext.knowledgehub.rnn.min_length_corpus', 300))
        self.sequence_length = config.get(
            u'ckanext.knowledgehub.rnn.sequence_length', 10)
        self.step = int(
            config.get(u'ckanext.knowledgehub.rnn.sentence_step', 3))
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

    def __check_paths_exist(self):
        weights_dir = os.path.dirname(self.weights_path)
        if not os.path.exists(weights_dir):
            os.makedirs(weights_dir)
        netwokr_dir = os.path.dirname(self.network_path)
        if not os.path.exists(netwokr_dir):
            os.makedirs(netwokr_dir)
        history_dir = os.path.dirname(self.history_path)
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)

        return self

    def __set_corpus(self):
        self.corpus = DataManager.get_corpus()
        self.data = self.corpus.lower()
        return self

    def __validate_corpus(self):
        if self.corpus_length > len(self.data):
            msg = ('The minimum length of the corpus is {}, '
                   'current corpus has {}').format(
                       int(self.corpus_length), len(self.data)
                   )
            raise toolkit.ValidationError(msg)

        if len(self.data) <= self.sequence_length:
            msg = ('The length of the RNN sequence %d, given %d'
                    % (int(sequence_length), len(self.data)))

            raise toolkit.ValidationError(msg)

        return self

    def __process_corpus(self):
        self.unique_chars, self.char_indices, _ = \
            DataManager.prepare_corpus(self.data)
        return self

    def __set_x_y(self):
        sentences = []
        next_chars = []
        for i in range(0, len(self.data) - self.sequence_length, self.step):
            sentences.append(self.data[i: i + self.sequence_length])
            next_chars.append(self.data[i + self.sequence_length])

        self.logger.info('Number of training examples: %d ' % len(sentences))

        self.x = np.zeros((
            len(sentences),
            self.sequence_length,
            len(self.unique_chars)),
            dtype=np.bool
        )
        self.y = np.zeros((len(sentences), len(self.unique_chars)), dtype=np.bool)
        for i, sentence in enumerate(sentences):
            for t, char in enumerate(sentence):
                self.x[i, t, self.char_indices[char]] = 1
            self.y[i, self.char_indices[next_chars[i]]] = 1
        return self

    def __prepare_model(self):
        self.model.add(LSTM(128, input_shape=(
            self.sequence_length, len(self.unique_chars))))
        self.model.add(Dense(len(self.unique_chars)))
        self.model.add(Activation('softmax'))

        optimizer=RMSprop(lr=0.01)
        self.model.compile(
            loss='categorical_crossentropy',
            optimizer=optimizer,
            metrics=['accuracy'])

        return self

    def __train_model(self):
        earlyStopping = EarlyStopping(
            monitor='val_loss',
            patience=10,
            verbose=0,
            mode='min'
                )
        mcp_save =ModelCheckpoint(
            self.temp_weigths_path,
            save_best_only=True,
            save_weights_only=True,
            monitor='val_loss',
            mode='min'
        )
        reduce_lr_loss = ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.1,
            patience=7,
            verbose=1,
            epsilon=1e-4,
            mode='min'
        )
        self.history = self.model.fit(
            self.x,
            self.y,
            validation_split=0.05,
            batch_size=128,
            epochs=self.epochs,
            shuffle=True,
            callbacks=[
                earlyStopping,
                mcp_save,
                reduce_lr_loss
            ]
        ).history

        return self

    def __save_model(self):
        try:
            lock_model_network = FileLock('%s.lock' % self.network_path)
            lock_model_weigths = FileLock('%s.lock' % self.weights_path)

            with lock_model_network.acquire(timeout=1000):
                with lock_model_weigths.acquire(timeout=1000):
                    if os.path.exists(self.weights_path):
                        os.remove(self.weights_path)
                    os.rename(self.temp_weigths_path, self.weights_path)

                    with open(self.network_path, "w") as json_file:
                        model_json = self.model.to_json()
                        json_file.write(model_json)

                    toolkit.get_action('corpus_create')(
                        {'ignore_auth': True},
                        {'corpus': self.data}
                    )
        except Exception as e:
            self.logger.debug('Error while saving RNN model: %s' % str(e))
            raise e
        finally:
            os.remove('%s.lock' % self.network_path)
            os.remove('%s.lock' % self.weights_path)

        return self

    def __save_history(self):
        try:
            pickle.dump(self.history, open(self.history_path, "wb"))
        except Exception as e:
            self.logger.debug('Error while saving RNN history: %s' % str(e))
            raise e

    def run(self):
        self.__check_paths_exist().\
        __set_corpus().\
        __validate_corpus().\
        __process_corpus().\
        __set_x_y().\
        __prepare_model().\
        __train_model().\
        __save_model().\
        __save_history()
