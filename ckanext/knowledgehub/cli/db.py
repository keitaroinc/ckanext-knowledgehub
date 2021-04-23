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
from ckanext.knowledgehub.model.theme import theme_db_setup
from ckanext.knowledgehub.model.research_question import setup as rq_db_setup
from ckanext.knowledgehub.model.sub_theme import setup as sub_theme_db_setup
from ckanext.knowledgehub.model.dashboard import setup as dashboard_db_setup
from ckanext.knowledgehub.model.rnn_corpus import setup as rnn_corpus_setup
from ckanext.knowledgehub.model.resource_validation import (
    setup as resource_validation_setup
)
from ckanext.knowledgehub.model.resource_feedback import (
    setup as resource_feedback_setup
)
from ckanext.knowledgehub.model.kwh_data import (
    setup as kwh_data_setup
)
from ckanext.knowledgehub.model.intents import setup as intents_db_setup
from ckanext.knowledgehub.model.query import setup as query_db_setup
from ckanext.knowledgehub.model.ml import setup as ml_db_setup
from ckanext.knowledgehub.model.data_quality import setup as data_quality_setup
from ckanext.knowledgehub.model.resource_validate import (
    setup as resource_validate_setup
)
from ckanext.knowledgehub.model.user_profile import setup as user_profile_setup
from ckanext.knowledgehub.model.keyword import setup as keyword_setup
from ckanext.knowledgehub.model.visualization import (
    setup as extend_resource_view_setup
)
from ckanext.knowledgehub.model.notification import setup as notification_setup
from ckanext.knowledgehub.model.posts import setup as posts_setup
from ckanext.knowledgehub.model.comments import setup as comments_setup
from ckanext.knowledgehub.model.likes import setup as likes_setup
from ckanext.knowledgehub.model.request_audit import (
    setup as request_audit_setup
)


log = logging.getLogger(__name__)


@click.group()
def db():
    pass


@db.command(u'init', short_help=u'Initialize Knowledgehub tables')
def init():
    init_db()


def init_db():
    u'''Initialising the Knowledgehub tables'''
    log.info(u"Initialize Knowledgehub tables")
    try:
        theme_db_setup()
        sub_theme_db_setup()
        rq_db_setup()
        dashboard_db_setup()
        resource_feedback_setup()
        resource_validation_setup()
        kwh_data_setup()
        rnn_corpus_setup()
        intents_db_setup()
        query_db_setup()
        ml_db_setup()
        data_quality_setup()
        resource_validate_setup()
        user_profile_setup()
        keyword_setup()
        extend_resource_view_setup()
        notification_setup()
        posts_setup()
        comments_setup()
        likes_setup()
        request_audit_setup()
    except Exception as e:
        error_shout(e)
    else:
        click.secho(
            u'Initialising Knowledgehub tables: SUCCESS',
            fg=u'green',
            bold=True)
