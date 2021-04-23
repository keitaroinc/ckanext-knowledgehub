# encoding: utf-8

"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

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
