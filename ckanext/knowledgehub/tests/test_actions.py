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
from ckanext.knowledgehub.logic.action import create as create_actions
from ckanext.knowledgehub.logic.action import get as get_actions
from ckanext.knowledgehub.logic.action import delete as delete_actions
from ckanext.knowledgehub.logic.action import update as update_actions
from ckanext.knowledgehub.tests.helpers import (User,
                                                create_dataset,
                                                mock_pylons)
from ckanext.datastore.logic.action import datastore_create

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
            'title': 'Internal Dashboard',
            'description': 'Dashboard description',
            'type': 'internal'
        }
        dashboard = create_actions.dashboard_create(context, data_dict)

        assert_equals(dashboard.get('name'), data_dict.get('name'))

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
            'title': 'Internal Dashboard',
            'description': 'Dashboard description',
            'type': 'internal'
        }
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
            'title': 'Internal Dashboard',
            'description': 'Dashboard description',
            'type': 'internal'
        }
        dashboard = create_actions.dashboard_create(context, data_dict)

        result = delete_actions.dashboard_delete(
            context,
            {'id': dashboard.get('id')}
        )

        assert_equals(result.get('message'), 'Dashboard deleted.')


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

        assert_equals(rsc_updated, None)

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
            'title': 'Internal Dashboard',
            'description': 'Dashboard description',
            'type': 'internal'
        }
        dashboard = create_actions.dashboard_create(context, data_dict)

        data_dict['id'] = dashboard.get('id')
        data_dict['title'] = 'Internal Dashboard Updated'
        dashboard_updated = update_actions.dashboard_update(
            context,
            data_dict
        )

        assert_equals(dashboard_updated.get('title'), data_dict.get('title'))

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
            'map_resource':"https://www.grandconcourse.ca/map/data/GCPoints.geojson"

        }
        res = get_actions.knowledgehub_get_geojson_properties(context, data_dict)
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
            'sql_string' : sql_str
        }
        res_data = get_actions.get_resource_data(context, data_dict)

        assert_equals(len(res_data), 7)

    #TODO: the next two tests give error when we add filters, the end result
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