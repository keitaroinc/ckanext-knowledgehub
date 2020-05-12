"""Tests for actions.py."""

import os
import mock
import nose.tools
import json
from itertools import product

from ckan.tests import factories
from ckan import plugins
from ckan.tests import helpers
from ckan.plugins import toolkit
from ckan import logic
from ckan import model
from datetime import datetime
from ckan.common import config
from collections import namedtuple

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
                                                get_context,
                                                get_regular_user_context)
from ckanext.knowledgehub.model import (
    Dashboard,
    ResearchQuestion,
    Visualization,
    DataQualityMetrics as DataQualityMetricsModel,
    ResourceValidate,
    Posts,
    AssignedAccessRequest,
    AccessRequest,
)
from ckanext.knowledgehub.model.keyword import extend_tag_table
from ckanext.knowledgehub.lib.rnn import PredictiveSearchWorker
from ckanext.knowledgehub.lib.util import monkey_patch
from ckanext.datastore.logic.action import datastore_create
from hdx.data.dataset import Dataset
from hdx.data.resource import Resource
from hdx.hdx_configuration import Configuration

from pysolr import Results

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises
assert_not_equals = nose.tools.assert_not_equals
assert_true = nose.tools.assert_true


class _test_user:

    fullname = 'Joe Bloggs'


class ActionsBase(helpers.FunctionalTestBase):

    @monkey_patch(Configuration, 'delete', mock.Mock())
    @monkey_patch(Configuration, 'create', mock.Mock())
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
        extend_tag_table()
        config['ckanext.knowledgehub.rnn.min_length_corpus'] = 100

        if not plugins.plugin_loaded('datastore'):
            plugins.load('datastore')
        if not plugins.plugin_loaded('datapusher'):
            plugins.load('datapusher')
        if not plugins.plugin_loaded('knowledgehub'):
            plugins.load('knowledgehub')

    @classmethod
    def teardown_class(self):
        if not plugins.plugin_loaded('knowledgehub'):
            plugins.unload('knowledgehub')
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

    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
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

    @monkey_patch(Visualization, 'add_to_index', mock.Mock())
    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_view_create(self):
        Dataset.read_from_hdx.return_value = ""
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

    @monkey_patch(Dashboard, 'add_to_index', mock.Mock())
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

        data_dict = {
            'name': 'external-test',
            'title': 'External test',
            'description': 'Test',
            'type': 'external',
            'source': 'link',
            'shared_with_users': json.dumps(['user1', 'user2'])
        }
        dashboard = create_actions.dashboard_create(context, data_dict)
        assert_equals(dashboard.get('name'), data_dict.get('name'))

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_feedback(self):
        Dataset.read_from_hdx.return_value = ""
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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_validation_create(self):
        Dataset.read_from_hdx.return_value = ""
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
            'title': 'Refugees in Syria',
            'description': 'Number of refugees in Syria 2020'
        }
        kwh_data = create_actions.kwh_data_create(context, data_dict)

        assert_equals(kwh_data.get('title'), data_dict.get('title'))

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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_merge_all_data(self):
        Dataset.read_from_hdx.return_value = ""
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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_validate_create(self):
        Dataset.read_from_hdx.return_value = ""
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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    @monkey_patch(Resource, 'delete_from_hdx', mock.Mock())
    def test_delete_package_from_hdx(self):

        ctx = get_context()
        dataset = create_dataset()
        delete_pkg = delete_actions.delete_package_from_hdx(ctx, dataset)
        assert_equals(delete_pkg, None)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    @monkey_patch(Dataset, 'check_required_fields', mock.Mock())
    @monkey_patch(Dataset, 'create_in_hdx', mock.Mock())
    @monkey_patch(Dataset, 'get_resources', mock.Mock())
    @monkey_patch(Resource, 'delete_from_hdx', mock.Mock())
    @monkey_patch(Dataset, '__init__', mock.Mock())
    def test_upsert_dataset_to_hdx(self):

        Dataset.check_required_fields.return_value = ""
        Dataset.create_in_hdx.return_value = ""
        Resource.delete_from_hdx = ""

        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        dataset = create_dataset()
        dataset['license_id'] = 'cc-by'
        dataset['private'] = True
        dataset['dataset_source'] = 'knowledgehub'
        dataset['dataset_date'] = '2020-03-11 14:37:05.887534'
        dataset['data_update_frequency'] = -1
        dataset['methodology'] = 'http://www.opendefinition.org/licenses/cc-by'
        dataset['num_resources'] = 1
        dataset['url'] = None
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://people.sc.fsu.edu/~jburkardt/data/csv/addresses.csv',
            description='Some description here',
            created='2020-03-10 00:13:47.641641',
            name='resource name',
            format='CSV',
            id='a7ae9f30-ff91-405c-bf7b-926017bcb9ac'
        )
        Dataset.read_from_hdx.return_value = {
            'name': dataset['name'],
            'title': dataset['title'],
            'notes': dataset['notes'],
            'maintainer': dataset['maintainer'],
            'owner_org': dataset['name'],
            'license_id': dataset['license_id'],
            'private': dataset['private'],
            'dataset_date': dataset['dataset_date'],
            'dataset_source': dataset['dataset_source'],
            'methodology': dataset['methodology'],
            'num_resources': dataset['num_resources'],
            'url': dataset['url'],
            'id': 'f32e1366-aa9e-4233-b77e-178ac0597295'
        }

        Dataset.__init__.return_value = None
        Dataset.get_resources.return_value = [{
            'package_id': dataset['id'],
            'url':
                'https://people.sc.fsu.edu/~jburkardt/data/csv/addresses.csv',
            'description':'Some description here',
            'created':'2020-03-10 00:13:47.641641',
            'name':'resource name',
            'format':'CSV',
            'id':'a7ae9f30-ff91-405c-bf7b-926017bcb9ac'
        }]
        hdx_newest_dataset = {
            'name': dataset['name'],
            'title': dataset['title'],
            'notes': dataset['notes'],
            'maintainer': dataset['maintainer'],
            'owner_org': dataset['name'],
            'license_id': dataset['license_id'],
            'private': dataset['private'],
            'dataset_date': dataset['dataset_date'],
            'dataset_source': dataset['dataset_source'],
            'methodology': dataset['methodology'],
            'num_resources': dataset['num_resources'],
            'url': dataset['url'],
            'id': 'f32e1366-aa9e-4233-b77e-178ac0597295'
        }
        data_dict = {
            'id': dataset.get('id'),
        }
        push_to_hdx = create_actions.upsert_dataset_to_hdx(context, data_dict)

        assert_equals(push_to_hdx, None)

    def test_post_create(self):
        context = get_context()
        rq = toolkit.get_action('research_question_create')(
            context,
            {
                'title': 'Test research question for post',
                'name': 'test-research-question-for-post',
            }
        )

        post = toolkit.get_action('post_create')(
            context,
            {
                'title': 'Test post rq 1',
                'description': 'Test post description',
                'entity_type': 'research_question',
                'entity_ref': rq['id']
            }
        )

        assert_true(post is not None)
        assert_true(post.get('id') is not None)
        assert_equals(post.get('title'), 'Test post rq 1')
        assert_equals(post.get('description'), 'Test post description')
        assert_equals(post.get('entity_type'), 'research_question')
        assert_equals(post.get('entity_ref'), rq['id'])
        assert_true(post.get('created_by') is not None)
        assert_true(post.get('created_at') is not None)

    def test_request_access(self):
        model.Session.query(AssignedAccessRequest).delete()
        model.Session.query(AccessRequest).delete()
        ctx = get_context()
        usr_ctx = get_regular_user_context()

        dataset = toolkit.get_action('package_create')(ctx, {
            'name': 'test-dataset',
            'title': 'Test Dataset',
        })

        req = toolkit.get_action('request_access')(usr_ctx, {
            'entity_type': 'dataset',
            'entity_ref': dataset['id'],
        })

        assert_true(req is not None)
        assert_equals(req.get('entity_type'), 'dataset')
        assert_equals(req.get('entity_ref'), dataset['id'])
        assert_equals(req.get('entity_title'), 'Test Dataset')
        assert_equals(req.get('user_id'), usr_ctx.get('auth_user_obj').id)

        result = toolkit.get_action('access_request_list')(ctx, {})
        assert_true(result is not None)
        assert_equals(result.get('count'), 1)


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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_view_list(self):
        Dataset.read_from_hdx.return_value = ""
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

    @monkey_patch(Dashboard, 'add_to_index', mock.Mock())
    @monkey_patch(Dashboard, 'search_index', mock.Mock())
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
        _Docs = namedtuple('_Docs', ['docs', 'hits'])
        Dashboard.search_index.return_value = _Docs([data_dict], 1)

        dashboard = create_actions.dashboard_create(context, data_dict)

        dashboard_show = get_actions.dashboard_show(
            context,
            {'id': dashboard.get('id')}
        )

        assert_equals(dashboard.get('name'), data_dict.get('name'))

        dashboard_list = get_actions.dashboard_list(context, {})

        assert_equals(dashboard_list.get('total'), 1)
        assert_equals(Dashboard.search_index.call_count, 1)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_user_feedback_show_list(self):
        Dataset.read_from_hdx.return_value = ""
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
            'title': 'Refugees in Syria',
            'description': 'Number of refugees in Syria 2020'
        }
        create_actions.kwh_data_create(context, data_dict)

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
        create_actions.corpus_create(context, data_dict)

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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_validate_status(self):
        Dataset.read_from_hdx.return_value = ""
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

    def test_get_predictions(self):
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

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(get_context(), data_dict)

        data_dict = {
            'type': 'theme',
            'title': 'Refugees in Syria',
            'description': 'Number of refugees in Syria 2020',
            'theme': theme['id']
        }
        create_actions.kwh_data_create(get_context(), data_dict)

        predicts = get_actions.get_predictions(
            get_context(),
            {'query': 'Refugees in Sy'}
        )

        assert(len(predicts) > 3)

    def test_get_all_organizations(self):
        ctx = get_context()
        toolkit.get_action('organization_create')({
            'ignore_auth': True,
            'user': ctx['user'],
        }, {
            'name': 'organization-one',
            'title': 'Organization One',
        })

        organizations = get_actions.get_all_organizations(ctx, {})
        assert_true(organizations is not None)
        assert_true(len(organizations) >= 1)

    def test_get_all_groups(self):
        ctx = get_context()
        toolkit.get_action('group_create')({
            'ignore_auth': True,
            'user': ctx['user'],
        }, {
            'name': 'group-one',
            'title': 'Group One',
        })

        groups = get_actions.get_all_groups(ctx, {})
        assert_true(groups is not None)
        assert_true(len(groups) >= 1)

    def test_group_list_for_user(self):
        ctx = get_regular_user_context()
        adm = get_context()
        group = toolkit.get_action('group_create')({
            'ignore_auth': True,
            'user': adm['user'],
        }, {
            'name': 'group-one',
            'title': 'Group One',
        })

        resp = toolkit.get_action('group_member_create')({
            'ignore_auth': True,
            'user': adm['user'],
        }, {
            'id': group['id'],
            'username': ctx['user'],
            'role': 'member',
        })

        groups = get_actions.group_list_for_user({
            'user': adm['user'],
        }, {
            'user': ctx['auth_user_obj'].id,
        })

        assert_true(groups is not None)
        assert_equals(len(groups), 1)

    def test_post_show(self):
        context = get_context()
        post = toolkit.get_action('post_create')(context, {
            'title': 'Post 3',
            'description': 'Post 3 description',
        })

        result = toolkit.get_action('post_show')(context, {
            'id': post['id'],
        })

        assert_true(result is not None)
        assert_true(result.get('author') is not None)

    @monkey_patch(Posts, 'search_index', mock.Mock())
    def test_post_search(self):
        context = get_context()
        p1 = toolkit.get_action('post_create')(context, {
            'title': 'Simple test',
            'description': 'simple test',
        })

        p2 = toolkit.get_action('post_create')(context, {
            'title': 'Other value',
            'description': 'other',
        })

        class _Results:

            def __init__(self, hits, docs, page, page_size, facets, stats):
                self.hits = hits
                self.docs = docs
                self.page = page
                self.page_size = page_size
                self.facets = facets
                self.stats = stats

        Posts.search_index.return_value = _Results(2, [p1, p2], 1, 20, {}, {})

        results = toolkit.get_action('post_search')(
            context,
            {
                'text': '*',
            }
        )

        assert_true(results is not None)
        assert_true(results.get('count', 0) == 2)

    def test_access_request_list(self):
        model.Session.query(AssignedAccessRequest).delete()
        model.Session.query(AccessRequest).delete()

        adm_ctx = get_context()
        usr1_ctx = get_regular_user_context()
        usr2_ctx = get_regular_user_context()

        dataset1 = toolkit.get_action('package_create')({
            'ignore_auth': True,
            'user': adm_ctx.get('user'),
            'auth_user_obj': adm_ctx.get('auth_user_obj'),
        }, {
            'name': 'acc-req-test-dataset-1',
            'title': 'Test Dataset 1',
        })

        dataset2 = toolkit.get_action('package_create')({
            'ignore_auth': True,
            'user': adm_ctx.get('user'),
            'auth_user_obj': adm_ctx.get('auth_user_obj'),
        }, {
            'name': 'acc-req-test-dataset-2',
            'title': 'Test Dataset 2',
        })

        for ctx, dst in product([usr1_ctx, usr2_ctx], [dataset1, dataset2]):
            toolkit.get_action('request_access')(ctx, {
                'entity_type': 'dataset',
                'entity_ref': dst['id'],
            })

        result = toolkit.get_action('access_request_list')(adm_ctx, {})

        assert_true(result is not None)
        assert_equals(result.get('count'), 4)
        assert_equals(len(result.get('results', [])), 4)


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

    @monkey_patch(ResearchQuestion, 'delete_from_index', mock.Mock())
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

    @monkey_patch(Dashboard, 'delete_from_index', mock.Mock())
    @monkey_patch(Dashboard, 'add_to_index', mock.Mock())
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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_validate_delete(self):
        Dataset.read_from_hdx.return_value = ""
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

    def test_package_delete(self):
        dataset = create_dataset()
        r = delete_actions.package_delete(get_context(), {'id': dataset['id']})

        assert_equals(r, None)

    def test_post_delete(self):
        context = get_context()
        post = toolkit.get_action('post_create')(context, {
            'title': 'Post 2',
            'description': 'Post 2 description',
        })

        result = toolkit.get_action('post_show')(context, {
            'id': post['id'],
        })

        assert_true(result is not None)

        toolkit.get_action('post_delete')(context, {'id': post['id']})

        not_found = False
        try:
            toolkit.get_action('post_show')(context, {'id': post['id']})
        except logic.NotFound:
            not_found = True
        assert_true(not_found)


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

    @monkey_patch(ResearchQuestion, 'update_index_doc', mock.Mock())
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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_update(self):
        Dataset.read_from_hdx.return_value = ""
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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_validation_update(self):
        Dataset.read_from_hdx.return_value = ""
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

        val_updated = update_actions.resource_validation_update(context,
                                                                data_dict)

        assert_equals(val_updated.get('admin'), data_dict.get('admin'))

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_validation_status(self):
        Dataset.read_from_hdx.return_value = ""
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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_validation_revert(self):
        Dataset.read_from_hdx.return_value = ""
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

    @monkey_patch(Visualization, 'update_index_doc', mock.Mock())
    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_view_update(self):
        Dataset.read_from_hdx.return_value = ""
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

    @monkey_patch(Dashboard, 'update_index_doc', mock.Mock())
    @monkey_patch(Dashboard, 'add_to_index', mock.Mock())
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
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'type': 'theme',
            'title': 'Refugees in Syria',
            'description': 'Number of refugees in Syria 2020',
            'theme': theme['id']
        }
        create_actions.kwh_data_create(context, data_dict)

        data_dict = {
            'type': 'theme',
            'entity_id': theme['id'],
            'title': 'Refugees in Syria',
            'description': 'Refugees in Syria updated'
        }

        kwh_data_updated = update_actions.kwh_data_update(
            context,
            data_dict
        )

        assert_equals(
            kwh_data_updated.get('description'),
            data_dict.get('description')
        )

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_validate_update(self):
        Dataset.read_from_hdx.return_value = ""
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

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_resource_data(self):
        Dataset.read_from_hdx.return_value = ""

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

    def test_access_request_grant(self):
        model.Session.query(AssignedAccessRequest).delete()
        model.Session.query(AccessRequest).delete()
        adm_ctx = get_context()
        usr_ctx = get_regular_user_context()

        dataset = toolkit.get_action('package_create')(adm_ctx, {
            'name': 'acc-req-test-dataset-3',
            'title': 'Access Req Test Dataset 3',
        })

        req = AccessRequest(
            entity_type='dataset',
            entity_ref=dataset['id'],
            entity_title=dataset['title'],
            entity_link='/dataset/link',
            user_id=usr_ctx['auth_user_obj'].id,
        )

        req.save()

        assigned = AssignedAccessRequest(
            request_id=req.id,
            user_id=adm_ctx['auth_user_obj'].id,
        )
        assigned.save()

        model.Session.flush()

        result = toolkit.get_action('access_request_grant')(adm_ctx, {
            'id': req.id,
        })

        assert_true(result is not None)
        assert_equals(result.get('status'), 'granted')
        assert_equals(result.get('resolved_by'), adm_ctx['auth_user_obj'].id)

    def test_access_request_decline(self):
        model.Session.query(AssignedAccessRequest).delete()
        model.Session.query(AccessRequest).delete()
        adm_ctx = get_context()
        usr_ctx = get_regular_user_context()

        dataset = toolkit.get_action('package_create')(adm_ctx, {
            'name': 'acc-req-test-dataset-4',
            'title': 'Access Req Test Dataset 4',
        })

        req = AccessRequest(
            entity_type='dataset',
            entity_ref=dataset['id'],
            entity_title=dataset['title'],
            entity_link='/dataset/link',
            user_id=usr_ctx['auth_user_obj'].id,
        )

        req.save()

        assigned = AssignedAccessRequest(
            request_id=req.id,
            user_id=adm_ctx['auth_user_obj'].id,
        )
        assigned.save()

        model.Session.flush()

        result = toolkit.get_action('access_request_decline')(adm_ctx, {
            'id': req.id,
        })

        assert_true(result is not None)
        assert_equals(result.get('status'), 'declined')
        assert_equals(result.get('resolved_by'), adm_ctx['auth_user_obj'].id)


class TestSearchIndexActions(helpers.FunctionalTestBase):

    @monkey_patch(Dashboard, 'search_index', mock.Mock())
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
        results = get_actions.search_dashboards(get_context(), {
            'text': 'aaa',
        })
        assert_true(results is not None)
        assert_equals(1, len(results.get('results')))
        Dashboard.search_index.called_once_with(q='text:aaa', rows=500)

    @monkey_patch(ResearchQuestion, 'search_index', mock.Mock())
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
        results = get_actions.search_research_questions(get_context(), {
            'text': 'aaa',
        })
        assert_true(results is not None)
        assert_equals(1, len(results.get('results')))
        ResearchQuestion.search_index.called_once_with(q='text:aaa', rows=500)

    @monkey_patch(Visualization, 'search_index', mock.Mock())
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
        results = get_actions.search_visualizations(get_context(), {
            'text': 'aaa',
        })
        assert_true(results is not None)
        assert_equals(1, len(results.get('results')))
        Visualization.search_index.called_once_with(q='text:aaa', rows=500)


class TestDataQualityActions(helpers.FunctionalTestBase):

    @monkey_patch(DataQualityMetricsModel, 'get_resource_metrics', mock.Mock())
    def test_get_resource_data_quality(self):
        now = datetime.now()
        dq = DataQualityMetricsModel(
            type='resource',
            ref_id='dq-1',
            created_at=now,
            accuracy=10.5,
            completeness=99.9,
            consistency=90.8,
            timeliness='+01:00:00',
            uniqueness=30.0,
            validity=80.0,
            metrics={'key': 'val'},
        )

        DataQualityMetricsModel.get_resource_metrics.return_value = dq

        result = get_actions.resource_data_quality({
            'ignore_auth': True,
        }, {
            'id': 'dq-1',
        })
        assert_true(result is not None)
        assert_equals(result, {
            'calculated_on': now.isoformat(),
            'resource_id': 'dq-1',
            'accuracy': 10.5,
            'completeness': 99.9,
            'consistency': 90.8,
            'timeliness': '+01:00:00',
            'uniqueness': 30.0,
            'validity': 80.0,
            'details': {'key': 'val'},
        })

    @monkey_patch(DataQualityMetricsModel, 'get_dataset_metrics', mock.Mock())
    def test_get_package_data_quality(self):
        now = datetime.now()
        dq = DataQualityMetricsModel(
            type='package',
            ref_id='dq-1',
            created_at=now,
            accuracy=10.5,
            completeness=99.9,
            consistency=90.8,
            timeliness='+01:00:00',
            uniqueness=30.0,
            validity=80.0,
            metrics={'key': 'val'},
        )

        DataQualityMetricsModel.get_dataset_metrics.return_value = dq

        result = get_actions.package_data_quality({
            'ignore_auth': True,
        }, {
            'id': 'dq-1',
        })
        assert_true(result is not None)
        assert_equals(result, {
            'calculated_on': now.isoformat(),
            'package_id': 'dq-1',
            'accuracy': 10.5,
            'completeness': 99.9,
            'consistency': 90.8,
            'timeliness': '+01:00:00',
            'uniqueness': 30.0,
            'validity': 80.0,
            'details': {'key': 'val'},
        })

    @monkey_patch(DataQualityMetricsModel, 'get', mock.Mock())
    def test_resource_data_quality_update(self):
        now = datetime.now()
        dq = DataQualityMetricsModel(
            type='resource',
            ref_id='dq-1',
            created_at=now,
            accuracy=10.5,
            completeness=99.9,
            consistency=90.8,
            timeliness='+01:00:00',
            uniqueness=30.0,
            validity=80.0,
            metrics={'key': 'val'},
        )

        dq.save = mock.Mock()

        DataQualityMetricsModel.get.return_value = dq

        result = update_actions.resource_data_quality_update({
            'ignore_auth': True,
        }, {
            'id': 'dq-1',
            'accuracy': {
                'value': 10.0,
                'total': 10,
                'accurate': 1,
                'inaccurate': 9,
            },
            'completeness': {
                'value': 90.0,
                'total': 100,
                'complete': 90,
            },
            'consistency': {
                'value': 80.0,
                'total': 100,
                'consistent': 80,
            },
            'timeliness': {
                'value': '+10:00:00',
                'total': 100*3600,
                'average': 10*3600,
                'records': 10,
            },
            'uniqueness': {
                'value': 70.0,
                'total': 100,
                'unique': 70,
            },
            'validity': {
                'value': 60.0,
                'total': 100,
                'valid': 60,
            }
        })

        assert_true(result is not None)
        assert_not_equals(result, {
            'calculated_on': now.isoformat(),
            'resource_id': 'dq-1',
            'accuracy': 10.0,
            'completeness': 90.0,
            'consistency': 80.0,
            'timeliness': '+10:00:00',
            'uniqueness': 70.0,
            'validity': 60.0,
            'details': {
                'accuracy': {
                    'value': 10.0,
                    'total': 10,
                    'accurate': 1,
                    'inaccurate': 9,
                    'manual': True,
                },
                'completeness': {
                    'value': 90.0,
                    'total': 100,
                    'complete': 90,
                    'manual': True,
                },
                'consistency': {
                    'value': 80.0,
                    'total': 100,
                    'consistent': 80,
                    'manual': True,
                },
                'timeliness': {
                    'value': '+10:00:00',
                    'total': 100*3600,
                    'average': 10*3600,
                    'records': 10,
                    'manual': True,
                },
                'uniqueness': {
                    'value': 70.0,
                    'total': 100,
                    'unique': 70,
                    'manual': True,
                },
                'validity': {
                    'value': 60.0,
                    'total': 100,
                    'valid': 60,
                    'manual': True,
                }
            },
        })

    @monkey_patch(DataQualityMetricsModel, 'get', mock.Mock())
    def test_package_data_quality_update(self):
        now = datetime.now()
        dq = DataQualityMetricsModel(
            type='package',
            ref_id='dq-1',
            created_at=now,
            accuracy=10.5,
            completeness=99.9,
            consistency=90.8,
            timeliness='+01:00:00',
            uniqueness=30.0,
            validity=80.0,
            metrics={'key': 'val'},
        )

        dq.save = mock.Mock()

        DataQualityMetricsModel.get.return_value = dq

        result = update_actions.package_data_quality_update({
            'ignore_auth': True,
        }, {
            'id': 'dq-1',
            'accuracy': {
                'value': 10.0,
                'total': 10,
                'accurate': 1,
                'inaccurate': 9,
            },
            'completeness': {
                'value': 90.0,
                'total': 100,
                'complete': 90,
            },
            'consistency': {
                'value': 80.0,
                'total': 100,
                'consistent': 80,
            },
            'timeliness': {
                'value': '+10:00:00',
                'total': 100*3600,
                'average': 10*3600,
                'records': 10,
            },
            'uniqueness': {
                'value': 70.0,
                'total': 100,
                'unique': 70,
            },
            'validity': {
                'value': 60.0,
                'total': 100,
                'valid': 60,
            }
        })

        assert_true(result is not None)
        assert_not_equals(result, {
            'calculated_on': now.isoformat(),
            'package_id': 'dq-1',
            'accuracy': 10.0,
            'completeness': 90.0,
            'consistency': 80.0,
            'timeliness': '+10:00:00',
            'uniqueness': 70.0,
            'validity': 60.0,
            'details': {
                'accuracy': {
                    'value': 10.0,
                    'total': 10,
                    'accurate': 1,
                    'inaccurate': 9,
                    'manual': True,
                },
                'completeness': {
                    'value': 90.0,
                    'total': 100,
                    'complete': 90,
                    'manual': True,
                },
                'consistency': {
                    'value': 80.0,
                    'total': 100,
                    'consistent': 80,
                    'manual': True,
                },
                'timeliness': {
                    'value': '+10:00:00',
                    'total': 100*3600,
                    'average': 10*3600,
                    'records': 10,
                    'manual': True,
                },
                'uniqueness': {
                    'value': 70.0,
                    'total': 100,
                    'unique': 70,
                    'manual': True,
                },
                'validity': {
                    'value': 60.0,
                    'total': 100,
                    'valid': 60,
                    'manual': True,
                }
            },
        })


class TestTagsActions(ActionsBase):

    __ctx = get_context()

    def _tag_create(self, name, vocabulary_id=None):
        return create_actions.tag_create(
            self.__ctx,
            {
                'name': name,
                'vocabulary_id': vocabulary_id
            }
        )

    def _vocabulary_create(self, name=None):
        return toolkit.get_action('vocabulary_create')(
            self.__ctx,
            {'name': name}
        )

    def test_tag_create(self):
        vocab = self._vocabulary_create('vocabulary1')
        tag1 = self._tag_create('tag1')
        tag2 = self._tag_create('tag2', vocab.get('id'))

        assert_equals(tag1['name'], 'tag1')
        assert_equals(tag2['name'], 'tag2')

    def test_tag_list(self):
        vocab = self._vocabulary_create('vocabulary1')
        tag1 = self._tag_create('tag1')
        tag2 = self._tag_create('tag2', vocab.get('id'))

        tags = get_actions.tag_list(self.__ctx, {})

        assert_equals(len(tags), 1)

        tags = get_actions.tag_list(
            self.__ctx,
            {'vocabulary_id': vocab.get('id')}
        )

        assert_equals(len(tags), 1)

    def test_tag_autocomplete(self):
        vocab = self._vocabulary_create('vocabulary1')
        tag1 = self._tag_create('tag1')
        # tag2 = self._tag_create('tag2')

        tags = get_actions.tag_autocomplete(self.__ctx, {'query': 'tag'})

        assert_equals(len(tags), 1)

    def test_tag_search(self):
        vocab = self._vocabulary_create('vocabulary1')
        tag1 = self._tag_create('tag1')
        # tag2 = self._tag_create('tag2')

        tags_dict = get_actions.tag_search(
            self.__ctx,
            {'query': 'tag'}
        )

        assert_equals(tags_dict.get('count'), 1)

    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    @monkey_patch(Visualization, 'add_to_index', mock.Mock())
    @monkey_patch(Dashboard, 'add_to_index', mock.Mock())
    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_tag_delete(self):
        Dataset.read_from_hdx.return_value = ""
        vocab = self._vocabulary_create('vocabulary1')
        tag1 = self._tag_create('tag1')

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(self.__ctx, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme['id']
        }
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        data_dict = {
            'name': 'rq-name',
            'title': 'Test title',
            'content': 'Research question?',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id'),
            'tags': tag1['name']
        }
        rq = create_actions.research_question_create(self.__ctx, data_dict)

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )
        data_dict = {
            'resource_id': resource.get('id'),
            'title': 'Visualization title',
            'description': 'Visualization description',
            'view_type': 'chart',
            'config': {
                "color": "#59a14f",
                "y_label": "Usage",
                "show_legend": "Yes"
            },
            'tags': tag1['name']
        }
        rsc_view = create_actions.resource_view_create(context, data_dict)

        data_dict = {
            'name': 'internal-dashboard',
            'title': 'Internal Dashboard (1)',
            'description': 'Dashboard description',
            'type': 'internal',
            'tags': tag1['name']
        }
        dashboard = create_actions.dashboard_create(context, data_dict)

        tags_dict = delete_actions.tag_delete(
            context,
            {'id': tag1['id']}
        )

        assert_equals(tags_dict.get('message'), 'The tag is deleted.')

    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    @monkey_patch(Visualization, 'add_to_index', mock.Mock())
    @monkey_patch(Dashboard, 'add_to_index', mock.Mock())
    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_group_tags(self):
        Dataset.read_from_hdx.return_value = ""
        vocab1 = self._vocabulary_create('vocabulary1')
        tag1 = self._tag_create('tag1')

        vocab2 = self._vocabulary_create('vocabulary2')
        tag2 = self._tag_create('tag2')

        data_dict = {
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(self.__ctx, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test title',
            'description': 'Test description',
            'theme': theme['id']
        }
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        data_dict = {
            'name': 'rq-name',
            'title': 'Test title',
            'content': 'Research question?',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id'),
            'tags': tag1['name']
        }
        rq = create_actions.research_question_create(self.__ctx, data_dict)

        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )
        data_dict = {
            'resource_id': resource.get('id'),
            'title': 'Visualization title',
            'description': 'Visualization description',
            'view_type': 'chart',
            'config': {
                "color": "#59a14f",
                "y_label": "Usage",
                "show_legend": "Yes"
            },
            'tags': tag1['name']
        }
        rsc_view = create_actions.resource_view_create(context, data_dict)

        data_dict = {
            'name': 'internal-dashboard',
            'title': 'Internal Dashboard (1)',
            'description': 'Dashboard description',
            'type': 'internal',
            'tags': tag1['name']
        }
        dashboard = create_actions.dashboard_create(context, data_dict)

        tags_dict = get_actions.group_tags(
            context,
            {'wrong_tags': [tag1['name']], 'new_tag': tag2['name']}
        )

        assert_equals(tags_dict.get('name'), tag2.get('name'))


class TestUserProfileActions(ActionsBase):

    def test_user_profile_create(self):
        context = get_regular_user_context()
        user_profile = create_actions.user_profile_create(context, {})
        assert_true(user_profile is not None)
        assert_equals(user_profile.get('user_id'), context['auth_user_obj'].id)

    @monkey_patch(toolkit, 'get_action', mock.MagicMock())
    def test_user_profile_update(self):

        def _get_action(action):
            if action != 'tag_show':
                raise Exception('Unmocked action: ' + action)

            def _tag_show(ctx, data):
                return {
                    'id': data['id'],
                    'name': data['id'],
                }

            return _tag_show

        toolkit.get_action.side_effect = _get_action

        context = get_regular_user_context()

        user_profile = update_actions.user_profile_update(context, {})
        assert_true(user_profile is not None)
        assert_equals(user_profile.get('user_id'), context['auth_user_obj'].id)

        interests = {
                'research_questions': ['rq-1', 'rq-2'],
                'keywords': ['kwd-1', 'kwd-2'],
                'tags': ['tag-1', 'tag-2'],
            }
        updated = update_actions.user_profile_update(context, {
            'user_notified': True,
            'interests': interests,
        })

        assert_true(updated is not None)
        assert_not_equals(updated, user_profile)
        assert_equals(updated.get('user_notified'), True)
        assert_equals(updated.get('interests'), interests)

    def test_user_profile_show(self):
        context = get_regular_user_context()
        create_actions.user_profile_create(context, {})
        user_profile = get_actions.user_profile_show(context, {})
        assert_true(user_profile is not None)
        assert_equals(user_profile.get('user_id'), context['auth_user_obj'].id)

    def test_user_profile_list(self):
        context = get_context()
        create_actions.user_profile_create(context, {})

        results = get_actions.user_profile_list(context, {})
        assert_true(results is not None)
        assert_true(isinstance(results, list))
        assert_true(len(results) > 0)


class TestNotificationsActions(ActionsBase):

    def test_notification_create(self):
        context = get_regular_user_context()
        notification = create_actions.notification_create(context, {
            'title': 'title',
            'description': 'test desc',
            'link': '/link',
            'image': '/image.url.png',
            'recepient': context['user'],
        })

        assert_true(notification is not None)
        assert_equals(notification.get('title'), 'title')
        assert_equals(notification.get('description'), 'test desc')
        assert_equals(notification.get('link'), '/link')
        assert_equals(notification.get('image'), '/image.url.png')
        assert_true(notification.get('id') is not None)
        assert_true(notification.get('created_at') is not None)
        assert_equals(notification.get('seen'), False)

    def test_notification_list(self):
        context = get_regular_user_context()
        for i in range(0, 3):
            create_actions.notification_create(context, {
                'title': 'title-%d' % i,
                'description': 'test desc %d' % i,
                'link': '/link',
                'image': '/image.url.png',
                'recepient': context['user'],
            })

        notifications = get_actions.notification_list(context, {})
        assert_true(notifications is not None)
        assert_equals(notifications.get('count'), 3)
        assert_equals(len(notifications.get('results', [])), 3)

    def test_notification_show(self):
        context = get_regular_user_context()

        notification = create_actions.notification_create(context, {
            'title': 'title',
            'description': 'test desc',
            'link': '/link',
            'image': '/image.url.png',
            'recepient': context['user'],
        })

        result = get_actions.notification_show(context, {
            'id': notification['id']
        })

        assert_equals(notification, result)

    def test_notifications_read(self):
        context = get_regular_user_context()

        notifications = []
        for i in range(0, 10):
            notification = create_actions.notification_create(context, {
                'title': 'title-%d' % i,
                'description': 'test desc %d' % i,
                'link': '/link',
                'image': '/image.url.png',
                'recepient': context['user'],
            })
            notifications.append(notification)

        update_actions.notifications_read(context, {
            'notifications': [n['id'] for n in notifications[0:3]],
        })

        unread = get_actions.notification_list(context, {})
        assert_true(unread is not None)
        assert_equals(unread.get('count'), 7)

        # now mark all as read
        update_actions.notifications_read(context, {})
        unread = get_actions.notification_list(context, {})
        assert_true(unread is not None)
        assert_equals(unread.get('count'), 0)
