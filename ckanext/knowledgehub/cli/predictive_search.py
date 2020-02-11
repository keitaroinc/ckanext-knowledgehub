# encoding: utf-8

import click
import logging

from ckanext.knowledgehub.cli import error_shout
from ckanext.knowledgehub.lib.rnn import PredictiveSearchWorker

log = logging.getLogger(__name__)


@click.group()
def predictive_search():
    pass


@predictive_search.command(u'train', short_help=u'Train the Tensorflow model')
def train():
    u'''Initialising the Knowledgehub tables'''
    log.info(u"Initialize Knowledgehub tables")
    try:
        worker = PredictiveSearchWorker()
        worker.run()
    except Exception as e:
        error_shout(e)
    else:
        click.secho(
            u'Training Tensorflow model: SUCCESS',
            fg=u'green',
            bold=True)
