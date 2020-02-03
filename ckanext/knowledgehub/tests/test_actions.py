"""Tests for actions.py."""

import os
import mock
import nose.tools

from ckan.tests import factories
from ckan import plugins
from ckan.tests import helpers
from ckan.plugins import toolkit
from ckan import model

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
from ckanext.knowledgehub.model.resource_validate import (
    setup as resource_validate_setup
)
from ckanext.knowledgehub.logic.action import create as create_actions
from ckanext.knowledgehub.logic.action import get as get_actions
from ckanext.knowledgehub.logic.action import delete as delete_actions
from ckanext.knowledgehub.logic.action import update as update_actions
from ckanext.knowledgehub import helpers as kwh_helpers
from ckanext.knowledgehub.tests.helpers import (User,
                                                create_dataset,
                                                mock_pylons,
                                                get_context)
from ckanext.knowledgehub.model import (Dashboard,
                                        ResearchQuestion,
                                        Visualization,
                                        ResourceValidate)
from ckanext.datastore.logic.action import datastore_create
from pysolr import Results

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises
assert_not_equals = nose.tools.assert_not_equals


class _test_user:

    fullname = 'Joe Bloggs'


class _monkey_patch:

    def __init__(self, obj, prop, patch_with):
        self.obj = obj
        self.prop = prop
        self.patch_with = patch_with

    def __call__(self, method):
        original_prop = None
        if hasattr(self.obj, self.prop):
            original_prop = getattr(self.obj, self.prop)

        def _with_patched(*args, **kwargs):
            # patch
            setattr(self.obj, self.prop, self.patch_with)
            try:
                return method(*args, **kwargs)
            finally:
                # unpatch
                if original_prop is not None:
                    setattr(self.obj, self.prop, original_prop)
                else:
                    delattr(self.obj, self.prop)
        _with_patched.__name__ = method.__name__
        _with_patched.__module__ = method.__module__
        _with_patched.__doc__ = method.__doc__
        return _with_patched


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
        resource_validate_setup()
        os.environ["CKAN_INI"] = './test.ini'
        if not plugins.plugin_loaded('datastore'):
            plugins.load('datastore')
        if not plugins.plugin_loaded('datapusher'):
            plugins.load('datapusher')

    @classmethod
    def teardown_class(self):
        if not plugins.plugin_loaded('datastore'):
            plugins.unload('datastore')
        if not plugins.plugin_loaded('datapusher'):
            plugins.unload('datapusher')


class TestKWHCreateActions(ActionsBase):

    def test_theme_create(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'ignore_auth': True
        }
        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        assert_equals(theme.get('name'), data_dict.get('name'))

    def test_sub_theme_create(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'ignore_auth': True
        }

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        assert_equals(sub_theme.get('name'), data_dict.get('name'))

    @_monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    def test_research_question_create(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True
        }

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        data_dict = {
            'name': 'rq-name',
            'title': 'Test title',
            'content': 'Research question?',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id')
        }
        rq = create_actions.research_question_create(context, data_dict)

        assert_equals(rq.get('name'), data_dict.get('name'))
        ResearchQuestion.add_to_index.assert_called_once()

    @_monkey_patch(Visualization, 'add_to_index', mock.Mock())
    def test_resource_view_create(self):

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'resource_id': resource.get('id'),
            'title': 'Visualization title',
            'description': 'Visualization description',
            'view_type': 'chart',
            'config': {
                "color": "#59a14f",
                "y_label": "Usage",
                "show_legend": "Yes"
            }
        }
        rsc_view = create_actions.resource_view_create(context, data_dict)

        assert_equals(rsc_view.get('package_id'), dataset.get('id'))
        Visualization.add_to_index.assert_called_once()

    @_monkey_patch(Dashboard, 'add_to_index', mock.Mock())
    def test_dashboard_create(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'name': 'internal-dashboard',
            'title': 'Internal Dashboard (1)',
            'description': 'Dashboard description',
            'type': 'internal'
        }
        dashboard = create_actions.dashboard_create(context, data_dict)

        assert_equals(dashboard.get('name'), data_dict.get('name'))
        Dashboard.add_to_index.assert_called_once()

    def test_resource_feedback(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        data_dict = {
            'type': 'useful',
            'dataset': dataset.get('id'),
            'resource': resource.get('id')
        }
        rf = create_actions.resource_feedback(context, data_dict)

        assert_equals(rf.get('dataset'), dataset.get('id'))
        assert_equals(rf.get('resource'), resource.get('id'))
 
    def test_resource_validation_create(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'ignore_auth': True
        }

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        data_dict = {
            'package_id': dataset['id'],
            'id': resource['id'],
            'url': resource['url'],
            'admin': user['name']
        }
        val = create_actions.resource_validation_create(context, data_dict)

        assert_equals(val.get('resource'), data_dict.get('id'))

    def test_kwh_data_create(self):
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
            'content': 'Refugees in Syria'
        }
        kwh_data = create_actions.kwh_data_create(context, data_dict)

        assert_equals(kwh_data.get('content'), data_dict.get('content'))

    def test_corpus_create(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'corpus': 'KHW corpus'
        }
        kwh_corpus = create_actions.corpus_create(context, data_dict)

        assert_equals(kwh_corpus.get('corpus'), data_dict.get('corpus'))

    def test_run_command(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'command': 'db init'
        }
        cmd = create_actions.run_command(context, data_dict)

        assert_equals(
            cmd,
            'Successfully run command: knowledgehub -c %s %s'
            % (os.environ.get('CKAN_INI'), data_dict.get('command'))
        )

    def test_user_query_create(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        query = create_actions.user_query_create(get_context(), data_dict)

        assert_equals(data_dict['query_text'], query['query_text'])
        assert_equals(data_dict['query_type'], query['query_type'])

    def test_user_intent_create(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        query = create_actions.user_query_create(get_context(), data_dict)

        data_dict = {
            'user_query_id': query['id'],
            'primary_category': 'dataset',
            'theme': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'sub_theme': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'research_question': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'inferred_transactional':
                'How many refugees are they in MENA Region in 2019?',
            'inferred_navigational': 'MENA Region, 2019',
            'inferred_informational': 'Refugees in MENA Region in 2019?'
        }

        intent = create_actions.user_intent_create(get_context(), data_dict)
        assert_equals(data_dict['inferred_transactional'],
                      intent['inferred_transactional'])
        assert_equals(data_dict['inferred_navigational'],
                      intent['inferred_navigational'])
        assert_equals(data_dict['inferred_informational'],
                      intent['inferred_informational'])

    def test_user_query_result_create(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        query = create_actions.user_query_create(get_context(), data_dict)

        data_dict = {
            "query_id": query['id'],
            "result_type": "dataset",
            "result_id": "bfbe08a1-24ab-493d-8892-72e399f6e1b7"
        }

        result = create_actions.user_query_result_create(
            get_context(),
            data_dict)

        assert_equals(data_dict['result_type'], result['result_type'])
        assert_equals(data_dict['result_id'], result['result_id'])
        assert_equals(data_dict['query_id'], result['query_id'])

    def test_merge_all_data(self):
        dataset = create_dataset()

        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            datastore_active=True,
        )
        data = {
            "resource_id": resource['id'],
            "fields": [{"id": "value", "type": "numeric"}],
            "records": [
                {"value": 1},
                {"value": 2},
                {"value": 3},
                {"value": 4},
                {"value": 5},
                {"value": 6},
                {"value": 7},
            ],
            "force": True
        }
        helpers.call_action('datastore_create', **data)

        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            datastore_active=True,
        )
        data = {
            "resource_id": resource['id'],
            "fields": [{"id": "value", "type": "numeric"}],
            "records": [
                {"value": 8},
                {"value": 9},
                {"value": 10},
                {"value": 11},
                {"value": 12},
                {"value": 13},
                {"value": 14},
            ],
            "force": True
        }
        helpers.call_action('datastore_create', **data)

        system_rsc = create_actions.merge_all_data(
            get_context(),
            {'id': dataset['id']}
        )

        assert_equals(
            system_rsc['resource_type'],
            kwh_helpers.SYSTEM_RESOURCE_TYPE
        )

    def test_member_create(self):
        dataset = create_dataset()
        data_dict = {
            'name': 'group1'
        }
        group = toolkit.get_action('group_create')(
            get_context(),
            data_dict
        )

        data_dict = {
            'id': group['id'],
            'object': dataset['id'],
            'object_type': 'package',
            'capacity': 'organization'
        }
        member = create_actions.member_create(
            get_context(),
            data_dict
        )

        assert_equals(member['group_id'], group['id'])
        assert_equals(member['state'], 'active')
        assert_equals(member['capacity'], member['capacity'])

    def test_resource_validate_create(self):
        user = factories.Sysadmin()
        test_auth_user = _test_user()
        context = {
            'user': user.get('name'),
            'auth_user_obj': test_auth_user,
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        data_dict = {
            'what': 'The resource is invalid!',
            'resource': resource.get('id')
        }
        rv = create_actions.resource_validate_create(context, data_dict)

        assert_equals(rv.get('what'), 'The resource is invalid!')
        assert_equals(rv.get('resource'), resource.get('id'))


class TestKWHGetActions(ActionsBase):

    def test_theme_show_list(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }
        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        theme_show = get_actions.theme_show(context, {'id': theme.get('id')})

        assert_equals(theme_show.get('name'), data_dict.get('name'))

        theme_list = get_actions.theme_list(context, {})

        assert_equals(theme_list.get('total'), 1)

    def test_sub_theme_show_list(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        sub_theme_show = get_actions.sub_theme_show(
            context,
            {'id': sub_theme.get('id')}
        )

        assert_equals(sub_theme_show.get('name'), data_dict.get('name'))

        sub_theme_list = get_actions.sub_theme_list(context, {})

        assert_equals(sub_theme_list.get('total'), 1)

    def test_research_question_show_list(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        data_dict = {
            'name': 'rq-name',
            'title': 'Test title',
            'content': 'Research question?',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id')
        }
        rq = create_actions.research_question_create(context, data_dict)

        rq_show = get_actions.research_question_show(
            context,
            {'id': rq.get('id')}
        )

        assert_equals(rq_show.get('name'), data_dict.get('name'))

        rq_list = get_actions.research_question_list(context, {})

        assert_equals(rq_list.get('total'), 1)

    def test_resource_view_list(self):
        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'resource_id': resource.get('id'),
            'title': 'Visualization title',
            'description': 'Visualization description',
            'view_type': 'chart',
            'config': {
                "color": "#59a14f",
                "y_label": "Usage",
                "show_legend": "Yes"
            }
        }
        rsc_view = create_actions.resource_view_create(context, data_dict)

        rsc_view_list = get_actions.resource_view_list(
            context,
            {'id': resource.get('id')}
        )

        assert_equals(
            rsc_view_list[0].get('view_type'),
            data_dict.get('view_type')
        )
        assert_equals(
            rsc_view_list[0].get('title'),
            data_dict.get('title')
        )

    @_monkey_patch(Dashboard, 'add_to_index', mock.Mock())
    def test_dashboard_show_list(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'name': 'internal-dashboard',
            'title': 'Internal Dashboard (2)',
            'description': 'Dashboard description',
            'type': 'internal'
        }

        def _mock_create_dashboard(data_dict):
            return data_dict

        Dashboard.add_to_index.side_effect = _mock_create_dashboard

        dashboard = create_actions.dashboard_create(context, data_dict)

        dashboard_show = get_actions.dashboard_show(
            context,
            {'id': dashboard.get('id')}
        )

        assert_equals(dashboard.get('name'), data_dict.get('name'))

        dashboard_list = get_actions.dashboard_list(context, {})

        assert_equals(dashboard_list.get('total'), 1)

    def test_resource_user_feedback_show_list(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        data_dict = {
            'type': 'useful',
            'dataset': dataset.get('id'),
            'resource': resource.get('id')
        }
        rf = create_actions.resource_feedback(context, data_dict)

        rf_show = get_actions.resource_user_feedback(
            context,
            {'resource': resource.get('id')}
        )

        assert_equals(rf_show[0].get('type'), data_dict.get('type'))

        rf_list = get_actions.resource_feedback_list(
            context,
            {
                'type': data_dict.get('type'),
                'dataset': dataset.get('id'),
                'resource': resource.get('id')
            }
        )

        assert_equals(rf_list.get('total'), 1)

    def test_get_rq_url(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        data_dict = {
            'name': 'rq-name',
            'title': 'Test title',
            'content': 'Research question?',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id')
        }
        rq = create_actions.research_question_create(context, data_dict)

        rq_url = get_actions.get_rq_url(context, {'name': rq.get('name')})

        assert_not_equals(rq_url, '')

    def test_kwh_data_list(self):
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
            'content': 'Refugees in Syria'
        }
        kwh_data = create_actions.kwh_data_create(context, data_dict)

        kwh_data_list = get_actions.kwh_data_list(context, {})

        assert_equals(kwh_data_list.get('total'), 1)

    def test_get_last_rnn_corpus(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'corpus': 'KHW corpus'
        }
        kwh_corpus = create_actions.corpus_create(context, data_dict)

        last_rnn_corpus = get_actions.get_last_rnn_corpus(context, {})

        assert_equals(last_rnn_corpus, data_dict.get('corpus'))

    def test_user_query_show(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        q = create_actions.user_query_create(get_context(), data_dict)
        q_shows = get_actions.user_query_show(get_context(), {'id': q['id']})

        assert_equals(q['query_text'], q_shows['query_text'])

    def test_user_intent_show(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        query = create_actions.user_query_create(get_context(), data_dict)

        data_dict = {
            'user_query_id': query['id'],
            'primary_category': 'dataset',
            'theme': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'sub_theme': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'research_question': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'inferred_transactional':
                'How many refugees are they in MENA Region in 2019?',
            'inferred_navigational': 'MENA Region, 2019',
            'inferred_informational': 'Refugees in MENA Region in 2019?'
        }

        i = create_actions.user_intent_create(get_context(), data_dict)
        i_show = get_actions.user_intent_show(get_context(), {'id': i['id']})

        assert_equals(i['inferred_transactional'],
                      i_show['inferred_transactional'])
        assert_equals(i['inferred_navigational'],
                      i_show['inferred_navigational'])
        assert_equals(i['inferred_informational'],
                      i_show['inferred_informational'])

    def test_user_query_result_show(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        query = create_actions.user_query_create(get_context(), data_dict)

        data_dict = {
            "query_id": query['id'],
            "result_type": "dataset",
            "result_id": "bfbe08a1-24ab-493d-8892-72e399f6e1b7"
        }

        r = create_actions.user_query_result_create(get_context(), data_dict)
        r_show = get_actions.user_query_result_show(
            get_context(),
            {'id': r['id']})

        assert_equals(r['result_type'], r_show['result_type'])
        assert_equals(r['result_id'], r_show['result_id'])
        assert_equals(r['query_id'], r_show['query_id'])

    def test_user_intent_list(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        query = create_actions.user_query_create(get_context(), data_dict)

        data_dict = {
            'user_query_id': query['id'],
            'primary_category': 'dataset',
            'theme': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'sub_theme': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'research_question': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'inferred_transactional':
                'How many refugees are they in MENA Region in 2019?',
            'inferred_navigational': 'MENA Region, 2019',
            'inferred_informational': 'Refugees in MENA Region in 2019?'
        }

        create_actions.user_intent_create(get_context(), data_dict)

        i_list = get_actions.user_intent_list(
            get_context(),
            {
                'page': 1,
                'limit': 10,
                'order_by': 'created_at asc'
            })

        assert_equals(i_list['total'], 1)
        assert_equals(i_list['page'], 1)
        assert_equals(i_list['size'], 10)
        assert_equals(len(i_list['items']), 1)

    def test_user_query_list(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        q = create_actions.user_query_create(get_context(), data_dict)

        q_list = get_actions.user_query_list(
            get_context(),
            {
                'page': 1,
                'limit': 10,
                'order_by': 'created_at asc'
            })

        assert_equals(q_list['total'], 1)
        assert_equals(q_list['page'], 1)
        assert_equals(q_list['size'], 10)
        assert_equals(len(q_list['items']), 1)

    def test_user_query_result_search(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        query = create_actions.user_query_create(get_context(), data_dict)

        data_dict = {
            "query_id": query['id'],
            "result_type": "dataset",
            "result_id": "bfbe08a1-24ab-493d-8892-72e399f6e1b7"
        }

        r = create_actions.user_query_result_create(get_context(), data_dict)

        r_search = get_actions.user_query_result_search(
            get_context(),
            {
                "q": "dataset",
                "page": 1,
                "limit": 10
            })

        assert_equals(r_search['total'], 1)
        assert_equals(r_search['page'], 1)
        assert_equals(r_search['size'], 10)
        assert_equals(len(r_search['items']), 1)

    def test_resource_validate_status(self):
        user = factories.Sysadmin()
        test_auth_user = _test_user()
        context = {
            'user': user.get('name'),
            'auth_user_obj': test_auth_user,
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }
        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )
        data_dict = {
            'what': 'The resource is invalid!',
            'resource': resource.get('id')
        }
        rv = create_actions.resource_validate_create(context, data_dict)

        resource_validate_show = get_actions.resource_validate_status(
            context, {'id': rv.get('resource')}
            )

        assert_equals(
            resource_validate_show.get('what'), data_dict.get('what')
            )


class TestKWHDeleteActions(ActionsBase):

    def test_theme_delete(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }
        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        result = delete_actions.theme_delete(context, {'id': theme.get('id')})

        assert_equals(result.get('message'), 'Theme deleted.')

    def test_sub_theme_delete(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'ignore_auth': True
        }

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        result = delete_actions.sub_theme_delete(
            context,
            {'id': sub_theme.get('id')}
        )

        assert_equals(result, 'OK')

    @_monkey_patch(ResearchQuestion, 'delete_from_index', mock.Mock())
    def test_research_question_delete(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True
        }

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        data_dict = {
            'name': 'rq-name',
            'title': 'Test title',
            'content': 'Research question?',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id')
        }
        rq = create_actions.research_question_create(context, data_dict)

        result = delete_actions.research_question_delete(
            context,
            {'id': rq.get('id')}
        )

        assert_equals(result, None)
        ResearchQuestion.delete_from_index.assert_called_once()

    @_monkey_patch(Dashboard, 'delete_from_index', mock.Mock())
    @_monkey_patch(Dashboard, 'add_to_index', mock.Mock())
    def test_dashboard_delete(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'name': 'internal-dashboard',
            'title': 'Internal Dashboard (3)',
            'description': 'Dashboard description',
            'type': 'internal'
        }

        def _mock_create_dashboard(data_dict):
            return data_dict

        Dashboard.add_to_index.side_effect = _mock_create_dashboard

        dashboard = create_actions.dashboard_create(context, data_dict)

        result = delete_actions.dashboard_delete(
            context,
            {'id': dashboard.get('id')}
        )

        assert_equals(result.get('message'), 'Dashboard deleted.')
        Dashboard.delete_from_index.assert_called_once()

    def test_user_intent_delete(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        query = create_actions.user_query_create(get_context(), data_dict)

        data_dict = {
            'user_query_id': query['id'],
            'primary_category': 'dataset',
            'theme': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'sub_theme': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'research_question': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'inferred_transactional':
                'How many refugees are they in MENA Region in 2019?',
            'inferred_navigational': 'MENA Region, 2019',
            'inferred_informational': 'Refugees in MENA Region in 2019?'
        }

        i = create_actions.user_intent_create(get_context(), data_dict)

        r = delete_actions.user_intent_delete(get_context(), {'id': i['id']})

        assert_equals(r, 'OK')

    def test_member_delete(self):
        dataset = create_dataset()
        data_dict = {
            'name': 'group1'
        }
        group = toolkit.get_action('group_create')(
            get_context(),
            data_dict
        )

        data_dict = {
            'id': group['id'],
            'object': dataset['id'],
            'object_type': 'package',
            'capacity': 'organization'
        }
        member = create_actions.member_create(
            get_context(),
            data_dict
        )

        data_dict.pop('capacity')
        delete_actions.member_delete(get_context(), data_dict)

        data_dict.pop('object')
        members = toolkit.get_action('member_list')(
            get_context(),
            data_dict
        )

        assert_equals(len(members), 0)

    def test_resource_validate_delete(self):
        user = factories.Sysadmin()
        test_auth_user = _test_user()
        context = {
            'user': user.get('name'),
            'auth_user_obj': test_auth_user,
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }
        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )
        data_dict = {
            'what': 'The resource is invalid!',
            'resource': resource.get('id')
        }
        rv = create_actions.resource_validate_create(context, data_dict)

        result = delete_actions.resource_validate_delete(
            context, {'id': rv.get('resource')}
            )

        assert_equals(
            result.get('message'),
            'Validation report of the resource is deleted.'
            )


class TestKWHUpdateActions(ActionsBase):

    def test_theme_update(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }
        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict['title'] = 'Test title updated'
        updated_theme = update_actions.theme_update(context, data_dict)

        assert_equals(updated_theme.get('title'), data_dict.get('title'))

    def test_sub_theme_update(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'ignore_auth': True
        }

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        data_dict['id'] = sub_theme.get('id')
        data_dict['title'] = 'Test title updated'
        sub_theme_updated = update_actions.sub_theme_update(context, data_dict)

        assert_equals(sub_theme_updated.get('title'), data_dict.get('title'))

    @_monkey_patch(ResearchQuestion, 'update_index_doc', mock.Mock())
    def test_research_question_update(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True
        }

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        data_dict = {
            'name': 'rq-name',
            'title': 'Test title',
            'content': 'Research question',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id')
        }
        rq = create_actions.research_question_create(context, data_dict)

        data_dict['id'] = rq.get('id')
        data_dict['title'] = 'Research question updated'
        rq_updated = update_actions.research_question_update(
            context,
            data_dict
        )

        assert_equals(rq_updated.get('title'), data_dict.get('title'))
        ResearchQuestion.update_index_doc.assert_called_once()

    def test_resource_update(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        data_dict = {
            'id': resource.get('id'),
            'name': 'Name updated',
            'schema': '',
            'validation_options': '',
            'db_type': None
        }

        rsc_updated = update_actions.resource_update(context, data_dict)

        assert_not_equals(rsc_updated, None)
    
    def test_resource_validation_update(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        data_dict = {
            'package_id': dataset['id'],
            'id': resource['id'],
            'url': resource['url'],
            'admin': user['name']
        }
        val = create_actions.resource_validation_create(context, data_dict)

        new_user = factories.Sysadmin()
        context = {
            'user': new_user.get('name'),
            'auth_user_obj': User(new_user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'package_id': dataset['id'],
            'id': resource['id'],
            'user': user['name'],
            'admin': new_user['name']
        }

        val_updated = update_actions.resource_validation_update(context, data_dict)

        assert_equals(val_updated.get('admin'), data_dict.get('admin'))
    
    def test_resource_validation_status(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        data_dict = {
            'package_id': dataset['id'],
            'id': resource['id'],
            'url': resource['url'],
            'admin': user['name']
        }
        val = create_actions.resource_validation_create(context, data_dict)

        data_dict = {
            'resource': resource['id']
        }

        val_updated = update_actions.resource_validation_status(
            context, data_dict)

        assert_equals(val_updated.get('status'), 'validated')
    
    def test_resource_validation_revert(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        data_dict = {
            'package_id': dataset['id'],
            'id': resource['id'],
            'url': resource['url'],
            'admin': user['name']
        }
        val = create_actions.resource_validation_create(context, data_dict)

        data_dict = {
            'resource': resource['id']
        }

        val_updated = update_actions.resource_validation_status(
            context, data_dict)

        val_reverted = update_actions.resource_validation_revert(
            context, data_dict)

        assert_equals(val_reverted.get('status'), 'not_validated')

    @_monkey_patch(Visualization, 'update_index_doc', mock.Mock())
    def test_resource_view_update(self):
        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'resource_id': resource.get('id'),
            'title': 'Visualization title',
            'description': 'Visualization description',
            'view_type': 'chart',
            'config': {
                "color": "#59a14f",
                "y_label": "Usage",
                "show_legend": "Yes"
            }
        }
        rsc_view = create_actions.resource_view_create(context, data_dict)

        data_dict['id'] = rsc_view.get('id')
        data_dict['title'] = 'Visualization title updated'
        rsc_view_updated = update_actions.resource_view_update(
            context,
            data_dict
        )

        assert_equals(
            rsc_view_updated.get('title'),
            data_dict.get('title')
        )
        Visualization.update_index_doc.assert_called_once()

    @_monkey_patch(Dashboard, 'update_index_doc', mock.Mock())
    @_monkey_patch(Dashboard, 'add_to_index', mock.Mock())
    def test_dashboard_update(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'name': 'internal-dashboard',
            'title': 'Internal Dashboard (4)',
            'description': 'Dashboard description',
            'type': 'internal'
        }

        def _mock_create_dashboard(data_dict):
            return data_dict

        Dashboard.add_to_index.side_effect = _mock_create_dashboard

        dashboard = create_actions.dashboard_create(context, data_dict)

        data_dict['id'] = dashboard.get('id')
        data_dict['title'] = 'Internal Dashboard Updated'
        dashboard_updated = update_actions.dashboard_update(
            context,
            data_dict
        )

        assert_equals(dashboard_updated.get('title'), data_dict.get('title'))
        Dashboard.update_index_doc.assert_called_once()

    def test_kwh_data_update(self):
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
            'content': 'Refugees in Syria'
        }
        kwh_data = create_actions.kwh_data_create(context, data_dict)

        data_dict = {
            'type': 'theme',
            'old_content': 'Refugees in Syria',
            'new_content': 'Refugees in Syria updated'
        }

        kwh_data_updated = update_actions.kwh_data_update(
            context,
            data_dict
        )

        assert_equals(
            kwh_data_updated.get('content'),
            data_dict.get('new_content')
        )

    def test_resource_validate_update(self):
        user = factories.Sysadmin()
        test_auth_user = _test_user()
        context = {
            'user': user.get('name'),
            'auth_user_obj': test_auth_user,
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )

        data_dict = {
            'what': 'The resource is invalid!',
            'resource': resource.get('id')
        }
        rv = create_actions.resource_validate_create(context, data_dict)

        data_dict['id'] = rv.get('resource')
        data_dict['what'] = 'The resource is valid'
        rv_updated = update_actions.resource_validate_update(
            context,
            data_dict
        )

        assert_equals(rv_updated.get('what'), data_dict.get('what'))

    def test_user_intent_update(self):
        data_dict = {
            'query_text': 'How many refugees are they in MENA Region in 2019?',
            'query_type': 'dataset'
        }

        query = create_actions.user_query_create(get_context(), data_dict)

        data_dict = {
            'user_query_id': query['id'],
            'primary_category': 'dataset',
            'theme': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'sub_theme': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'research_question': '08563b0c-9c51-4daa-b33c-0892b1878a6d',
            'inferred_transactional':
                'How many refugees are they in MENA Region in 2019?',
            'inferred_navigational': 'MENA Region, 2019',
            'inferred_informational': 'Refugees in MENA Region in 2019?'
        }

        i = create_actions.user_intent_create(get_context(), data_dict)

        i_update = update_actions.user_intent_update(
            get_context(),
            {
                "id": i['id'],
                "primary_category": "dashboard"
            })

        assert_equals(i_update['primary_category'], 'dashboard')

    def test_knowledgehub_get_geojson_properties(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        data_dict = {
            'map_resource':
                "https://www.grandconcourse.ca/map/data/GCPoints.geojson"

        }
        res = get_actions.knowledgehub_get_geojson_properties(context,
                                                              data_dict)
        assert_equals(len(res), 26)

    def test_get_resource_data(self):

        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }
        dataset = create_dataset()
        data = {
            "fields": [{"id": "value", "type": "numeric"}],
            "records": [
                {"value": 0},
                {"value": 1},
                {"value": 2},
                {"value": 3},
                {"value": 5},
                {"value": 6},
                {"value": 7},
            ],
            "force": True
        }
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            datastore_active=True,
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)
        sql_str = u'''SELECT DISTINCT "{column}"
         FROM "{resource}" '''.format(
            column="value",
            resource=resource['id']
        )
        data_dict = {
            'sql_string': sql_str
        }
        res_data = get_actions.get_resource_data(context, data_dict)

        assert_equals(len(res_data), 7)

    # TODO: the next two tests give error when we add filters, the end result
    #       is written for printing errors only

    # def test_get_chart_data(self):

    #     user = factories.Sysadmin()
    #     context = {
    #         'user': user.get('name'),
    #         'auth_user_obj': User(user.get('id')),
    #         'ignore_auth': True,
    #         'model': model,
    #         'session': model.Session
    #     }
    #     dataset = create_dataset()
    #     data = {
    #        "fields": [{"id": "value", "type": "numeric"}],
    #         "records": [
    #             {"value": 0},
    #             {"value": 1},
    #             {"value": 2},
    #             {"value": 3},
    #             {"value": 5},
    #             {"value": 6},
    #             {"value": 7},
    #         ],
    #         "filters": {"value" : 0},
    #         "force": True
    #     }
    #     resource = factories.Resource(
    #         schema='',
    #         validation_options='',
    #         package_id=dataset['id'],
    #         datastore_active=True,
    #     )
    #     data['resource_id'] = resource['id']
    #     helpers.call_action('datastore_create', **data)
    #     sql_str = u'''SELECT DISTINCT "{column}"
    #     FROM "{resource}" GROUP BY "{column}"'''.format(
    #         column="value",
    #         resource=resource['id']
    #     )
    #     data_dict = {
    #         'resource_id': resource['id'],
    #         'category': "records",
    #         'sql_string': sql_str,
    #         'filters': { "value": 0 },
    #         'x_axis': "value",
    #         'y_axis': "value"

    #     }
    #     chart_data = get_actions.get_chart_data(context, data_dict)
    #     assert_equals(chart_data, "")

    # def test_visualizations_for_rq(self):

    #     user = factories.Sysadmin()
    #     context = {
    #         'user': user.get('name'),
    #         'auth_user_obj': User(user.get('id')),
    #         'ignore_auth': True,
    #         'model': model,
    #         'session': model.Session
    #     }

    #     data_dict = {
    #         'name': 'theme-name',
    #         'title': 'Test theme',
    #         'description': 'Test description'
    #     }
    #     theme = create_actions.theme_create(context, data_dict)

    #     data_dict = {
    #         'name': 'sub-theme-name',
    #         'title': 'Test sub-theme',
    #         'description': 'Test description',
    #         'theme': theme.get('id')
    #     }
    #     sub_theme = create_actions.sub_theme_create(context, data_dict)

    #     data_dict = {
    #         'name': 'rq',
    #         'title': 'rq',
    #         'content': 'random',
    #         'theme': theme.get('id'),
    #         'sub_theme': sub_theme.get('id')
    #     }

    #     rq = create_actions.research_question_create(context, data_dict)
    #     dataset = create_dataset(
    #         extras= [{"research_question": "Random"}]
    #     )
    #     print(dataset)
    #     resource = factories.Resource(
    #         schema='',
    #         validation_options='',
    #         package_id=dataset['id'],
    #     )
    #     data = {
    #        "fields": [{"id": "value", "type": "numeric"}],
    #         "records": [
    #             {"value": 0},
    #             {"value": 1},
    #             {"value": 2},
    #             {"value": 3},
    #             {"value": 5},
    #             {"value": 6},
    #             {"value": 7},
    #         ],
    #         "force": True,
    #         "resource_id": resource.get('id'),
    #         "research_question": "random"
    #     }

    #     data_dict = {
    #             'resource_id': resource.get('id'),
    #             'title': 'Visualization title',
    #             'description': 'Visualization description',
    #             'view_type': 'chart',
    #             'config': {
    #                 "color": "#59a14f",
    #                 "y_label": "Usage",
    #                 "show_legend": "Yes"
    #             }
    #         }
    #     data['resource_id'] = resource.get('id')
    #     helpers.call_action('datastore_create', **data)
    #     rsc_view = create_actions.resource_view_create(context, data_dict)
    #     #print(rsc_view)
    #     data_dict_rq = {
    #         'research_question': "random"
    #     }

    #     res = get_actions.visualizations_for_rq(context, data_dict_rq)
    #     assert_equals(res, "")


class SearchIndexActionsTest(helpers.FunctionalTestBase):

    @_monkey_patch(Dashboard, 'search_index', mock.Mock())
    def test_search_dashboards(self):
        Dashboard.search_index.return_value = Results({
            'response': {
                'docs': [{
                    'id': 'aaa',
                    'p1': 'v1',
                    'p2': 'v2',
                }],
                'numFound': 1,
            }
        })
        results = get_actions.search_dashboards({}, {
            'text': 'aaa',
        })
        assert_equals(1, len(results))
        Dashboard.search_index.called_once_with(q='text:aaa', rows=500)

    @_monkey_patch(ResearchQuestion, 'search_index', mock.Mock())
    def test_search_research_questions(self):
        ResearchQuestion.search_index.return_value = Results({
            'response': {
                'docs': [{
                    'id': 'aaa',
                    'p1': 'v1',
                    'p2': 'v2',
                }],
                'numFound': 1,
            }
        })
        results = get_actions.search_research_questions({}, {
            'text': 'aaa',
        })
        assert_equals(1, len(results))
        ResearchQuestion.search_index.called_once_with(q='text:aaa', rows=500)

    @_monkey_patch(Visualization, 'search_index', mock.Mock())
    def test_search_visualizations(self):
        Visualization.search_index.return_value = Results({
            'response': {
                'docs': [{
                    'id': 'aaa',
                    'p1': 'v1',
                    'p2': 'v2',
                }],
                'numFound': 1,
            }
        })
        results = get_actions.search_visualizations({}, {
            'text': 'aaa',
        })
        assert_equals(1, len(results))
        Visualization.search_index.called_once_with(q='text:aaa', rows=500)
