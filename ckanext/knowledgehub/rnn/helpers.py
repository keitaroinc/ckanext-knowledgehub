import logging
import os

import heapq
import numpy as np
import tensorflow as tf
from keras.models import load_model

from ckan.plugins import toolkit
from ckan import logic
from ckan.common import config


log = logging.getLogger(__name__)


def prepare_rnn_corpus(corpus):
    unique_chars = sorted(list(set(corpus)))
    char_indices = dict((c, i) for i, c in enumerate(unique_chars))
    indices_char = dict((i, c) for i, c in enumerate(unique_chars))

    return unique_chars, char_indices, indices_char


def prepare_input(text, unique_chars, char_indices):
    sequence_length = int(
        config.get(u'ckanext.knowledgehub.rnn.sequence_length', 10)
    )
    x = np.zeros((1, sequence_length, len(unique_chars)))
    for t, char in enumerate(text):
        x[0, t, char_indices[char]] = 1.

    return x


def sample(preds, top_n=3):
    preds = np.asarray(preds).astype('float64')
    preds = np.log(preds)
    exp_preds = np.exp(preds)
    preds = exp_preds / np.sum(exp_preds)

    return heapq.nlargest(top_n, range(len(preds)), preds.take)


def predict_completion(model, text, unique_chars, char_indices, indices_char):
    original_text = text
    generated = text
    completion = ''
    while True:
        x = prepare_input(text, unique_chars, char_indices)
        preds = model.predict(x, verbose=0)[0]
        next_index = sample(preds, top_n=1)[0]
        next_char = indices_char[next_index]
        text = text[1:] + next_char
        if next_char in ['?', '!', '.', ',', ' ']:
            return completion

        completion += next_char
        if (len(original_text + completion) + 2 > len(original_text) and
                next_char == ' '):

            return completion


def predict_completions(text):
    text = text.lower()
    try:
        c = toolkit.get_action('get_last_rnn_corpus')({}, {}).lower()
        unique_chars, char_indices, indices_char = prepare_rnn_corpus(c)
        unique_chars_text = sorted(list(set(text)))

        for char in unique_chars_text:
            if char not in unique_chars:
                return []
    except Exception as e:
        log.debug('Error while preparing the RNN corpus: %s' % str(e))
        return []

    sequence_length = int(
        config.get(u'ckanext.knowledgehub.rnn.sequence_length', 10)
    )
    if sequence_length > len(text):
        return []

    text = text[-sequence_length:].lower()

    model_path = config.get(
        u'ckanext.knowledgehub.rnn.model',
        './keras_model.h5'
    )
    if not os.path.isfile(model_path):
        log.debug('Error: RNN model does not exist!')
        return []

    try:
        n = int(config.get(u'ckanext.knowledgehub.rnn.number_prediction', 3))
        graph = tf.Graph()
        with graph.as_default():
            session = tf.Session()
            with session.as_default():
                model = load_model(model_path)
                x = prepare_input(text, unique_chars, char_indices)
                preds = model.predict(x, verbose=0)[0]
                next_indices = sample(preds, n)
                return [
                    indices_char[idx] +
                    predict_completion(
                        model,
                        text[1:] + indices_char[idx],
                        unique_chars,
                        char_indices,
                        indices_char
                    ) for idx in next_indices]
    except Exception as e:
        log.debug('Error while prediction: %s' % str(e))
        return []
