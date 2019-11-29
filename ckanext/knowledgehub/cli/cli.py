# encoding: utf-8

import logging

import click

from ckanext.knowledgehub.cli import (click_config_option,
                                      db,
                                      load_config,
                                      predictive_search,
                                      index)
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
