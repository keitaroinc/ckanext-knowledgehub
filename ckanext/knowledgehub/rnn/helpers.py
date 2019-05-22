import logging
import os

import heapq
import numpy as np
from keras.models import load_model

from ckan.plugins import toolkit
from ckan import logic
from ckan.common import config


log = logging.getLogger(__name__)


def get_kwh_data():
    corpus = ''
    try:
        kwh_data = toolkit.get_action('kwh_data_list')({}, {})
    except Exception as e:
        log.debug('Error while loading KnowledgeHub data: %s' % str(e))
        return corpus

    if kwh_data.get('total'):
        data = kwh_data.get('data', [])
        for entry in data:
            corpus += ' %s' % entry.get('content')

    return corpus


def prepare_rnn_corpus(corpus):
    chars = sorted(list(set(corpus)))
    char_indices = dict((c, i) for i, c in enumerate(chars))
    indices_char = dict((i, c) for i, c in enumerate(chars))

    return chars, char_indices, indices_char


def prepare_input(text, chars, char_indices):
    sequence_length = int(
        config.get(u'ckanext.knowledgehub.rnn.sequence_length', 10)
    )
    x = np.zeros((1, sequence_length, len(chars)))
    for t, char in enumerate(text):
        x[0, t, char_indices[char]] = 1.

    return x


def sample(preds, top_n=3):
    preds = np.asarray(preds).astype('float64')
    preds = np.log(preds)
    exp_preds = np.exp(preds)
    preds = exp_preds / np.sum(exp_preds)

    return heapq.nlargest(top_n, range(len(preds)), preds.take)


def predict_completion(model, text, chars, char_indices, indices_char):
    original_text = text
    generated = text
    completion = ''
    while True:
        x = prepare_input(text, chars, char_indices)
        preds = model.predict(x, verbose=0)[0]
        next_index = sample(preds, top_n=1)[0]
        next_char = indices_char[next_index]
        text = text[1:] + next_char
        completion += next_char

        if (len(original_text + completion) + 2 > len(original_text) and
                next_char == ' '):

            return completion


def predict_completions(text, n=3):
    c = toolkit.get_action('get_last_rnn_corpus')({}, {})
    chars, char_indices, indices_char = prepare_rnn_corpus(c)

    model_path = config.get(
        u'ckanext.knowledgehub.rnn.model',
        './keras_model.h5'
    )
    if not os.path.isfile(model_path):
        log.debug('Error: RNN model does not exist!')
        return []

    model = load_model(model_path)
    x = prepare_input(text, chars, char_indices)
    preds = model.predict(x, verbose=0)[0]
    next_indices = sample(preds, n)
    return [
        indices_char[idx] +
        predict_completion(
            model,
            text[1:] + indices_char[idx],
            chars,
            char_indices,
            indices_char
        ) for idx in next_indices]
