import os
import logging
import pickle

import numpy as np
import tensorflow as tf

from keras.models import Sequential, load_model
from keras.layers import Dense, Activation
from keras.layers import LSTM, Dropout
from keras.layers import TimeDistributed
from keras.layers.core import Dense, Activation, Dropout, RepeatVector
from keras.optimizers import RMSprop
from keras.callbacks import EarlyStopping

from ckan.common import config
from ckan.plugins import toolkit

from ckanext.knowledgehub.rnn import helpers as rnn_helper
from ckanext.knowledgehub import helpers as h


np.random.seed(42)
tf.set_random_seed(42)
log = logging.getLogger(__name__)


def learn():
    try:
        data = rnn_helper.get_kwh_data()
    except Exception as e:
        log.debug('Error while training the model: %s' % str(e))

    chars, char_indices, indices_char = rnn_helper.prepare_rnn_corpus(data)
    log.info('unique chars: %d' % len(chars))

    sequence_length = int(
        config.get(u'ckanext.knowledgehub.rnn.sequence_length', 10)
    )
    if len(data) <= sequence_length:
        return

    step = int(config.get(u'ckanext.knowledgehub.rnn.sentence_step', 3))
    sentences = []
    next_chars = []
    for i in range(0, len(data) - sequence_length, step):
        sentences.append(data[i: i + sequence_length])
        next_chars.append(data[i + sequence_length])

    log.info('num training examples: %d ' % len(sentences))

    X = np.zeros((len(sentences), sequence_length, len(chars)), dtype=np.bool)
    y = np.zeros((len(sentences), len(chars)), dtype=np.bool)
    for i, sentence in enumerate(sentences):
        for t, char in enumerate(sentence):
            X[i, t, char_indices[char]] = 1
        y[i, char_indices[next_chars[i]]] = 1

    history = ''
    try:
        model = Sequential()
        model.add(LSTM(128, input_shape=(sequence_length, len(chars))))
        model.add(Dense(len(chars)))
        model.add(Activation('softmax'))

        optimizer = RMSprop(lr=0.01)
        model.compile(
            loss='categorical_crossentropy',
            optimizer=optimizer,
            metrics=['accuracy'])

        callbacks = [
            EarlyStopping(
                monitor='val_acc',
                min_delta=0.001,
                patience=5,
                verbose=1,
                mode='auto',
                baseline=None,
                restore_best_weights=False
            )
        ]
        history = model.fit(
            X,
            y,
            validation_split=0.05,
            batch_size=128,
            epochs=int(config.get(u'ckanext.knowledgehub.rnn.max_epochs', 50)),
            shuffle=True,
            callbacks=callbacks
        ).history
    except Exception as e:
        log.debug('Error while creating RNN model: %s' % str(e))
        return

    model_path = config.get(
        u'ckanext.knowledgehub.rnn.model',
        './keras_model.h5'
    )
    model_dir = os.path.dirname(model_path)
    if not os.path.exists(model_dir):
        try:
            os.makedirs(model_dir)
        except Exception as e:
            log.debug('Error while creating RNN model DIR: %s' % str(e))
            return

    try:
        model.save(model_path)
        toolkit.get_action('corpus_create')({}, {
            'corpus': data
        })
    except Exception as e:
        log.debug('Error while saving RNN model: %s' % str(e))
        return

    history_path = config.get(
        u'ckanext.knowledgehub.rnn.history',
        './history.p'
    )
    history_dir = os.path.dirname(history_path)
    if not os.path.exists(history_dir):
        try:
            os.makedirs(history_dir)
        except Exception as e:
            log.debug('Error while creating RNN history DIR: %s' % str(e))
            return

    try:
        pickle.dump(history, open(history_path, "wb"))
    except Exception as e:
        log.debug('Error while saving RNN history: %s' % str(e))
        return

    h.predict_completions('Test Total ', 3)
