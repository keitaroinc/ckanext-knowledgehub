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
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

from ckan.common import config
from ckan.plugins import toolkit

from ckanext.knowledgehub.rnn import helpers as rnn_h
from ckanext.knowledgehub import helpers as h


np.random.seed(42)
tf.set_random_seed(42)
log = logging.getLogger(__name__)


def learn():
    try:
        original_data = h.get_kwh_data()
        data = original_data.lower()
    except Exception as e:
        log.debug('Error while training the model: %s' % str(e))

    unique_chars, char_indices, indices_char = rnn_h.prepare_rnn_corpus(data)
    log.info('unique chars: %d' % len(unique_chars))

    min_length_corpus = int(
        config.get(u'ckanext.knowledgehub.rnn.min_length_corpus', 300)
    )
    if min_length_corpus > len(data):
        return

    sequence_length = int(
        config.get(u'ckanext.knowledgehub.rnn.sequence_length', 15)
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

    X = np.zeros((
        len(sentences),
        sequence_length,
        len(unique_chars)),
        dtype=np.bool
    )
    y = np.zeros((len(sentences), len(unique_chars)), dtype=np.bool)
    for i, sentence in enumerate(sentences):
        for t, char in enumerate(sentence):
            X[i, t, char_indices[char]] = 1
        y[i, char_indices[next_chars[i]]] = 1

    history = ''
    try:
        model = Sequential()
        model.add(LSTM(128, input_shape=(sequence_length, len(unique_chars))))
        model.add(Dense(len(unique_chars)))
        model.add(Activation('softmax'))

        optimizer = RMSprop(lr=0.01)
        model.compile(
            loss='categorical_crossentropy',
            optimizer=optimizer,
            metrics=['accuracy'])

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

        # earlyStopping, mcp_save and reduce_lr_loss are used to avoid
        # overfitting and keep only best results
        earlyStopping = EarlyStopping(
            monitor='val_loss',
            patience=10,
            verbose=0,
            mode='min'
        )
        mcp_save = ModelCheckpoint(
            model_path,
            save_best_only=True,
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
        history = model.fit(
            X,
            y,
            validation_split=0.05,
            batch_size=128,
            epochs=int(config.get(u'ckanext.knowledgehub.rnn.max_epochs', 50)),
            shuffle=True,
            callbacks=[
                earlyStopping,
                mcp_save,
                reduce_lr_loss
            ]
        ).history
    except Exception as e:
        log.debug('Error while creating RNN model: %s' % str(e))
        return

    try:
        # model.save(model_path)
        toolkit.get_action('corpus_create')({}, {
            'corpus': original_data
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
