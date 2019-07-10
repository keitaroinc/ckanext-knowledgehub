"""Tests for rnn/worker.py."""

import os
import mock
import nose.tools

from ckan.tests import factories
from ckan import plugins
from ckan.tests import helpers
from ckan.plugins import toolkit
from ckan import model
from ckan.common import config

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
from ckanext.knowledgehub.logic.action import create as create_actions
from ckanext.knowledgehub.rnn.helpers import predict_completions
from ckanext.knowledgehub.rnn.worker import learn
from ckanext.knowledgehub.logic.action import get as get_actions
from ckanext.knowledgehub.tests.helpers import (User,
                                                create_dataset,
                                                mock_pylons)

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises
assert_not_equals = nose.tools.assert_not_equals


class ActionsBase(helpers.FunctionalTestBase):
    def setup(self):
        # helpers.reset_db()
        # theme_db_setup()
        # sub_theme_db_setup()
        # rq_db_setup()
        # dashboard_db_setup()
        # resource_feedback_setup()
        # kwh_data_setup()
        # rnn_corpus_setup()
        os.environ["CKAN_INI"] = 'subdir/test.ini'
        learn()

        if not plugins.plugin_loaded('knowledgehub'):
            plugins.load('knowledgehub')


class TestRNN(ActionsBase):

    def test_learn(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'type': 'theme',
            'content': ('Demo again Returns Resettlement Protection Social '
                        'Network Displacement Trends Labor Market Social '
                        'Cohesion Civil Documentation Demographics '
                        'Reception/Asylum Conditions Conditions of Return '
                        'What is the residential distribution of refugees in '
                        'COA? What is the change in total population numbers '
                        'before and after the crisis? What is the breakdown '
                        'of refugees by place of origin at governorate level?'
                        ' What are the monthly arrival trends by place of '
                        'origin at governorate level? What is the average '
                        'awaiting period in COA prior to registration? What '
                        'are the demographic characteristics of the '
                        'population?')
        }
        kwh_data = create_actions.kwh_data_create(context, data_dict)

        learn()

        model_path = config.get(
            u'ckanext.knowledgehub.rnn.model',
            './keras_model.h5'
        )

        assert_equals(os.path.isfile(model_path), True)

    def test_predict_completions(self):
        text = 'Demo again Returns Resettlement'
        completions = predict_completions(text)

        assert_equals(len(completions), 3)
