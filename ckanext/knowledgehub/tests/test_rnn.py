"""Tests for rnn/worker.py."""

import os
import nose.tools

from ckan import plugins
from ckan.tests import helpers
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
from ckanext.knowledgehub.lib.rnn import PredictiveSearchModel
from ckanext.knowledgehub.lib.rnn import PredictiveSearchWorker
from ckanext.knowledgehub.tests.helpers import get_context

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises
assert_not_equals = nose.tools.assert_not_equals


class ActionsBase(helpers.FunctionalTestBase):
    def setup(self):
        helpers.reset_db()
        theme_db_setup()
        sub_theme_db_setup()
        rq_db_setup()
        dashboard_db_setup()
        resource_feedback_setup()
        kwh_data_setup()
        rnn_corpus_setup()
        os.environ["CKAN_INI"] = 'subdir/test.ini'
        config['ckanext.knowledgehub.rnn.min_length_corpus'] = 100

        if not plugins.plugin_loaded('datastore'):
            plugins.load('datastore')
        if not plugins.plugin_loaded('knowledgehub'):
            plugins.load('knowledgehub')


class TestPredictiveSearchWorker(ActionsBase):

    def test_run(self):
        data_dict = {
            'type': 'theme',
            'title': 'Returns Resettlement Protection Social',
            'description': (
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
                'are the demographic characteristics of the population?'
            )
        }
        create_actions.kwh_data_create(get_context(), data_dict)

        worker = PredictiveSearchWorker()
        worker.run()

        assert_equals(os.path.isfile(worker.weights_path), True)
        assert_equals(os.path.isfile(worker.network_path), True)


class TestPredictiveSearchModel(ActionsBase):

    def test_predict(self):
        data_dict = {
            'type': 'theme',
            'title': 'Returns Resettlement Protection Social',
            'description': (
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
                'are the demographic characteristics of the population?'
            )
        }
        create_actions.kwh_data_create(get_context(), data_dict)

        worker = PredictiveSearchWorker()
        worker.run()

        text = 'Demo again Returns Resettlement'
        model = PredictiveSearchModel()
        predicts = model.predict(text)

        assert_equals(len(predicts), 3)
