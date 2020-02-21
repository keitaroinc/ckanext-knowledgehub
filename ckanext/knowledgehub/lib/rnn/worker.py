import logging
import os
import pickle
import time

import numpy as np
import tensorflow as tf
from filelock import FileLock

from keras.models import Sequential
from keras.layers import LSTM, Activation
from keras.layers.core import Dense, Activation
from keras.optimizers import RMSprop
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

from ckanext.knowledgehub.lib.rnn.data_manager import DataManager
from ckanext.knowledgehub.lib.rnn.config import PredictiveSearchConfig

from ckan.lib.navl import dictization_functions as df


np.random.seed(42)
tf.set_random_seed(42)


class PredictiveSearchWorker(PredictiveSearchConfig):
    ''' A worker that gets the kwh data, create corpus(training data),
    prepare the data for training, traing the model and save it.
    '''

    def __init__(self):
        super(PredictiveSearchWorker, self).__init__()
        self.model = Sequential()
        self.history = None
        self.corpus = None
        self.training_data = None
        self.unique_chars = None
        self.char_indices = None
        self.x = None
        self.y = None
        self.logger = logging.getLogger('ckanext.PredictiveSearchWorker')

    def __check_if_paths_exist(self):
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
        self.training_data = self.corpus.lower()
        self.training_data = ''.join(
            ch for ch in self.training_data if ch.isalnum() or ch == ' ')
        return self

    def __validate_corpus(self):
        if self.corpus_length > len(self.training_data):
            msg = ('The minimum length of the corpus is {}, '
                   'current corpus has {}').format(
                       int(self.corpus_length), len(self.training_data))
            self.logger.debug(msg)
            raise df.Invalid(msg)

        if len(self.training_data) <= self.sequence_length:
            msg = (
                'The length of the RNN sequence %d, given %d'
                % (int(sequence_length), len(self.training_data))
            )
            self.logger.debug(msg)
            raise df.Invalid(msg)

        return self

    def __process_corpus(self):
        self.unique_chars, self.char_indices, _ = \
            DataManager.prepare_corpus(self.training_data)
        return self

    def __set_x_y(self):
        sentences = []
        next_chars = []
        for i in range(
                0, len(self.training_data) - self.sequence_length, self.step):
            sentences.append(self.training_data[i: i + self.sequence_length])
            next_chars.append(self.training_data[i + self.sequence_length])

        self.logger.info('Number of training examples: %d ' % len(sentences))

        self.x = np.zeros((
            len(sentences),
            self.sequence_length,
            len(self.unique_chars)),
            dtype=np.bool
        )
        self.y = np.zeros(
            (len(sentences), len(self.unique_chars)), dtype=np.bool)
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

        optimizer = RMSprop(lr=0.01)
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
        mcp_save = ModelCheckpoint(
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

        try:
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
        except Exception as e:
            self.logger.debug('Error while training the model: %s' % str(e))
            raise e

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

                    DataManager.create_corpus(self.training_data)
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
        self.__check_if_paths_exist().\
             __set_corpus().\
             __validate_corpus().\
             __process_corpus().\
             __set_x_y().\
             __prepare_model().\
             __train_model().\
             __save_model().\
             __save_history()
