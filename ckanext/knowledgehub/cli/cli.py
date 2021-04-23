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

import logging

import click

from ckanext.knowledgehub.cli import (click_config_option,
                                      db,
                                      load_config,
                                      predictive_search,
                                      index,
                                      intents,
                                      quality)
from ckan.config.middleware import make_app

log = logging.getLogger(__name__)


class CkanCommand(object):

    def __init__(self, conf=None):
        self.config = load_config(conf)
        self.app = make_app(self.config.global_conf, **self.config.local_conf)


@click.group()
@click.help_option(u'-h', u'--help')
@click_config_option
@click.pass_context
def knowledgehub(ctx, config, *args, **kwargs):
    ctx.obj = CkanCommand(config)


knowledgehub.add_command(db.db)
knowledgehub.add_command(predictive_search.predictive_search)
knowledgehub.add_command(index.index)
knowledgehub.add_command(intents.intents)
knowledgehub.add_command(quality.quality)
