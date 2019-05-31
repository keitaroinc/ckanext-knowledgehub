# encoding: utf-8

import click
import logging

from ckanext.knowledgehub.cli import error_shout
from ckanext.knowledgehub.model.theme import theme_db_setup
from ckanext.knowledgehub.model.research_question import setup as rq_db_setup
from ckanext.knowledgehub.model.sub_theme import setup as sub_theme_db_setup
from ckanext.knowledgehub.model.dashboard import setup as dashboard_db_setup
from ckanext.knowledgehub.model.rnn_corpus import setup as rnn_corpus_setup
from ckanext.knowledgehub.model.resource_feedback import (
    setup as resource_feedback_setup
)
from ckanext.knowledgehub.model.kwh_data import (
    setup as kwh_data_setup
)

log = logging.getLogger(__name__)


@click.group()
def db():
    pass


@db.command(u'init', short_help=u'Initialize Knowledgehub tables')
def init():
    u'''Initialising the Knowledgehub tables'''
    log.info(u"Initialize Knowledgehub tables")
    try:
        theme_db_setup()
        sub_theme_db_setup()
        rq_db_setup()
        dashboard_db_setup()
        resource_feedback_setup()
        kwh_data_setup()
        rnn_corpus_setup()
    except Exception as e:
        error_shout(e)
    else:
        click.secho(
            u'Initialising Knowledgehub tables: SUCCESS',
            fg=u'green',
            bold=True)
