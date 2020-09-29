"""Tests for helpers.py."""

import os
import mock
import nose.tools
import json

from ckan.tests import factories
from ckan import plugins
from ckan.tests import helpers
from ckan.plugins import toolkit as toolkit
from ckan import model
from ckan.common import g
import ckan.common
from collections import namedtuple
from datetime import datetime, timedelta

from ckanext.knowledgehub.model.theme import theme_db_setup
from ckanext.knowledgehub.model.research_question import (
    setup as rq_db_setup,
    ResearchQuestion,
)
from ckanext.knowledgehub.model.sub_theme import setup as sub_theme_db_setup
from ckanext.knowledgehub.model.dashboard import (
    setup as dashboard_db_setup,
    Dashboard,
)
from ckanext.knowledgehub.model.visualization import Visualization
from ckanext.knowledgehub.model.rnn_corpus import setup as rnn_corpus_setup
from ckanext.knowledgehub.model.resource_feedback import (
    setup as resource_feedback_setup
)
from ckanext.knowledgehub.model.kwh_data import (
    setup as kwh_data_setup
)
from ckanext.knowledgehub.model import (
    Dashboard,
    ResearchQuestion,
    Visualization,
    DataQualityMetrics as DataQualityMetricsModel,
    ResourceValidate

)
from ckanext.knowledgehub.model.request_audit import RequestAudit
from ckanext.knowledgehub.lib import request_audit
from ckanext.knowledgehub.model.comments import CommentsRefStats
from ckanext.knowledgehub import helpers as kwh_helpers
from ckanext.knowledgehub.logic.action import create as create_actions
from ckanext.knowledgehub.logic.action import get as get_actions
from ckanext.knowledgehub.logic.action import delete as delete_actions
from ckanext.knowledgehub.logic.action import update as update_actions
from ckanext.knowledgehub.tests.helpers import (User,
                                                create_dataset,
                                                mock_pylons, 
                                                get_regular_user_context)
from ckanext.datastore.logic.action import datastore_create
from ckanext.datastore.logic.action import datastore_search
from ckanext.knowledgehub.lib.util import monkey_patch
from ckanext.knowledgehub.tests.helpers import get_context
from hdx.data.dataset import Dataset
from hdx.hdx_configuration import Configuration

assert_equals = nose.tools.assert_equals
assert_true = nose.tools.assert_true
assert_raises = nose.tools.assert_raises
assert_not_equals = nose.tools.assert_not_equals
raises = nose.tools.raises


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
        os.environ["CKAN_INI"] = 'subdir/test.ini'

        if not plugins.plugin_loaded('datastore'):
            plugins.load('datastore')
        if not plugins.plugin_loaded('datapusher'):
            plugins.load('datapusher')
        if not plugins.plugin_loaded('knowledgehub'):
            plugins.load('knowledgehub')

    @classmethod
    def teardown_class(self):
        if plugins.plugin_loaded('knowledgehub'):
            plugins.unload('knowledgehub')
        if not plugins.plugin_loaded('datastore'):
            plugins.unload('datastore')
        if not plugins.plugin_loaded('datapusher'):
            plugins.unload('datapusher')


class TestKWHHelpers(ActionsBase):

    def test_id_to_title(self):
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

        title = kwh_helpers.id_to_title('theme', theme.get('id'))

        assert_equals(title, theme.get('title'))

    def test_get_theme_options(self):
        mock_pylons()
        opts = kwh_helpers.get_theme_options()

        assert_equals(len(opts), 1)

    def test_get_sub_theme_options(self):
        mock_pylons()
        opts = kwh_helpers.get_sub_theme_options()

        assert_equals(len(opts), 1)

    def test_get_chart_types(self):
        mock_pylons()
        chart_types = kwh_helpers.get_chart_types()

        assert_equals(len(chart_types), 13)

    def test_get_uuid(self):
        uid = kwh_helpers.get_uuid()

        assert_equals(uid.version, 4)

    def test_get_visualization_size(self):
        sizes = kwh_helpers.get_visualization_size()

        assert_equals(len(sizes), 3)

    def test_get_color_scheme(self):
        colors = kwh_helpers.get_color_scheme()

        assert_equals(len(colors), 8)

    def test_get_map_color_scheme(self):
        map_colors = kwh_helpers.get_map_color_scheme()

        assert_equals(len(map_colors), 6)

    def test_parse_json(self):
        json_str = '{"name": "test"}'

        json = kwh_helpers.parse_json(json_str)

        assert_equals(isinstance(json, dict), True)

    def test_get_chart_sort(self):
        sorts = kwh_helpers.get_chart_sort()

        assert_equals(len(sorts), 3)

    def test_get_tick_text_rotation(self):
        rotations = kwh_helpers.get_tick_text_rotation()

        assert_equals(len(rotations), 4)

    def test_get_data_formats(self):
        data_formats = kwh_helpers.get_data_formats(3)

        assert_equals(len(data_formats), 3)

    def test_dump_json(self):
        arr = ['foo', {'bar': ('baz', None, 1.0, 2)}]
        json_str = kwh_helpers.dump_json(arr)

        assert_equals(isinstance(json_str, str), True)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_last_visuals(self):
        Dataset.read_from_hdx.return_value = ""
        dataset = create_dataset()
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts',
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
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

        last_visuals = kwh_helpers.get_last_visuals()

        assert_equals(len(last_visuals), 0)

    @monkey_patch(Dashboard, 'add_to_index', mock.Mock())
    def test_get_rqs_dashboards(self):
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
            'title': 'Internal Dashboard (5)',
            'description': 'Dashboard description',
            'type': 'internal'
        }
        dashboard = create_actions.dashboard_create(context, data_dict)

        ctx = get_context()

        g.user = ctx.get('user')
        g.userobj = ctx.get('auth_user_obj')
        try:
            dashboards = kwh_helpers.get_rqs_dashboards('Test')
        finally:
            del g.user
            del g.userobj

        assert_equals(len(dashboards), 0)

    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    def test_get_rq(self):
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

        rqs = kwh_helpers.get_rq(5, None)

        assert_equals(rq.get('title'), data_dict.get('title'))

    def test_pg_array_to_py_list(self):
        pg_array = '{{1,2,3},{4,5,6},{7,8,9}}'

        list = kwh_helpers.pg_array_to_py_list(pg_array)

        assert_equals(list, ['1', '2', '3', '4', '5', '6', '7', '8', '9'])

    def test_resource_view_icon(self):
        view = {
            'view_type': 'chart'
        }
        bar = kwh_helpers.resource_view_icon(view)
        assert_equals(bar, 'bar-chart')

        view['view_type'] = 'table'
        table = kwh_helpers.resource_view_icon(view)
        assert_equals(table, 'table')

        view['view_type'] = 'map'
        map = kwh_helpers.resource_view_icon(view)
        assert_equals(map, 'map')

    def test_knowledgehub_get_map_config(self):
        config = kwh_helpers.knowledgehub_get_map_config()

        assert_equals(isinstance(config, str), True)

    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    def test_get_single_rq(self):
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

        rq_show = kwh_helpers.get_single_rq(rq.get('id'))

        assert_equals(rq_show.get('title'), rq.get('title'))

    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    def test_rq_ids_to_titles(self):
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

        titles = kwh_helpers.rq_ids_to_titles([rq.get('id')])

        assert_equals(len(titles), 1)

    def test_get_dataset_url_path(self):
        url = 'http://host:port/lang/dataset'
        cut_url = kwh_helpers.get_dataset_url_path(url)

        assert_equals(cut_url, '/dataset')

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_feedback_count(self):
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
            schema='',
            validation_options='',
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts',
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )

        data_dict = {
            'type': 'useful',
            'dataset': dataset.get('id'),
            'resource': resource.get('id')
        }
        rf = create_actions.resource_feedback(context, data_dict)

        total = kwh_helpers.resource_feedback_count(
            data_dict.get('type'),
            data_dict.get('resource'),
            data_dict.get('dataset'))

        assert_equals(total, 1)

    @monkey_patch(Dashboard, 'add_to_index', mock.Mock())
    @monkey_patch(Dashboard, 'search_index', mock.Mock())
    def test_get_dashboards(self):
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
            'title': 'Internal Dashboard (6)',
            'description': 'Dashboard description',
            'type': 'internal'
        }
        dashboard = create_actions.dashboard_create(context, data_dict)

        _Docs = namedtuple('_Docs', ['docs', 'hits'])
        Dashboard.search_index.return_value = _Docs([data_dict], 1)

        dashboards = kwh_helpers.get_dashboards(ctx=context)

        assert_equals(len(dashboards), 1)
        assert_equals(Dashboard.search_index.call_count, 1)

    def test_remove_space_for_url(self):
        url = 'http://host:port/lang/data set'

        new_url = kwh_helpers.remove_space_for_url(url)
        assert_equals(new_url, 'http://host:port/lang/data-set')

    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    def test_get_rq_options(self):

        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True
        }

        data_dict = {
            'name': 'theme-name',
            'title': 'Test theme',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name',
            'title': 'Test sub-theme',
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
        titles = kwh_helpers.get_rq_options(context, True)

        assert_equals(len(titles), 1)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_rq_ids(self):
        Dataset.read_from_hdx.return_value = ""
        dataset = create_dataset()
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts',
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        rqs = kwh_helpers.get_rq_ids(resource['id'])
        assert_equals(len(rqs), 8)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_geojson_resources(self):
        Dataset.read_from_hdx.return_value = ""

        dataset = create_dataset()
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            format='geojson',
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        resources = kwh_helpers.get_geojson_resources()
        assert_equals(len(resources), 1)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    def test_get_rq_titles_from_res(self):
        Dataset.read_from_hdx.return_value = ""
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True
        }

        data_dict = {
            'name': 'theme-name1',
            'title': 'Test theme1',
            'description': 'Test description1'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict = {
            'name': 'sub-theme-name1',
            'title': 'Test sub-theme1',
            'description': 'Test description1',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict)

        data_dict = {
            'name': 'rq-name',
            'title': 'Test title1',
            'content': 'Research question?',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id')
        }

        rq1 = create_actions.research_question_create(context, data_dict)
        dataset = create_dataset(
            research_question=rq1['id']
        )
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts',
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'

        )

        titles = kwh_helpers.get_rq_titles_from_res(resource['id'])
        assert_equals(len(titles), 1)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_resource_view_get_fields(self):
        Dataset.read_from_hdx.return_value = ""
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
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)
        fields = kwh_helpers.resource_view_get_fields(resource)
        assert_equals(len(fields), 2)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_filter_values(self):
        Dataset.read_from_hdx.return_value = ""
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
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)
        fil_vals = kwh_helpers.get_filter_values(resource['id'], "value", [])
        assert_equals(len(fil_vals), 7)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_resource_columns(self):
        Dataset.read_from_hdx.return_value = ""
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
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)

        columns = kwh_helpers.get_resource_columns(resource.get('id'))
        assert_equals(len(columns), 1)



    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_resource_numeric_columns(self):
        Dataset.read_from_hdx.return_value = ""
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
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)

        columns = kwh_helpers.get_resource_numeric_columns(resource.get('id'))
        assert_equals(len(columns), 1)



    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_resource_data(self):
        Dataset.read_from_hdx.return_value = ""
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
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)
        sql_str = u'''SELECT DISTINCT "{column}"
         FROM "{resource}" '''.format(
            column="value",
            resource=resource['id']
        )
        res_data = kwh_helpers.get_resource_data(sql_str)

        assert_equals(len(res_data), 7)

    def test_get_geojson_properties(self):

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
        url = "https://www.grandconcourse.ca/map/data/GCPoints.geojson"
        res = kwh_helpers.get_geojson_properties(url, context.get('user'))
        assert_equals(len(res), 26)


    def test_format_date(self):
        date = "2019-11-21T10:09:05.900808"
        date_formated = kwh_helpers.format_date(date)
        assert_equals("2019-11-21 at 10:09", date_formated)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_dataset_data(self):
        Dataset.read_from_hdx.return_value = ""
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
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)

        d = kwh_helpers.get_dataset_data(dataset['id'])
        assert_equals(len(d['records']), 7)
        assert_equals(d['fields'][0]['type'], 'numeric')
        assert_equals(d['fields'][0]['id'], 'value')

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_dataset_data_err_msg(self):
        Dataset.read_from_hdx.return_value = ""
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
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)

        data = {
            "fields": [{"id": "age", "type": "numeric"}],
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
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)

        d = kwh_helpers.get_dataset_data(dataset['id'])
        assert(d.get('err_msg').startswith('The format of the data resource '
                                           '{resource} differs from the '
                                           'others'.format(
                                               resource=resource.get('name')
                                            )))

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_get_resource_filtered_data(self):
        Dataset.read_from_hdx.return_value = ""
        dataset = create_dataset()

        data = {
            "fields": [{"id": "value", "type": "numeric"}],
            "records": [
                {"value": "1"},
                {"value": "2"},
                {"value": "3"},
                {"value": "4"},
                {"value": "5"},
                {"value": "6"},
                {"value": "7"},
            ],
            "force": True
        }
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            datastore_active=True,
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)

        d = kwh_helpers.get_resource_filtered_data(resource['id'])
        assert_equals(d['records'], data['records'])

    def test_get_resource_filtered_data_exception(self):
        d = kwh_helpers.get_resource_filtered_data('failed-id')
        assert_equals(d['records'], [])

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_is_rsc_upload_datastore(self):
        Dataset.read_from_hdx.return_value = ""
        dataset = create_dataset()

        data = {
            "fields": [{"id": "value", "type": "numeric"}],
            "records": [
                {"value": "1"},
                {"value": "2"},
                {"value": "3"},
                {"value": "4"},
                {"value": "5"},
                {"value": "6"},
                {"value": "7"},
            ],
            "force": True
        }
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            datastore_active=True,
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        data['resource_id'] = resource['id']
        helpers.call_action('datastore_create', **data)

        b = kwh_helpers.is_rsc_upload_datastore(resource)
        assert_equals(b, False)

    def test_is_rsc_upload_datastore_exception(self):
        b = kwh_helpers.is_rsc_upload_datastore({})
        assert_equals(b, False)

    def test_check_resource_status(self):
        mock_pylons()
        dataset = create_dataset()
        resource_id = dataset['id']
        status = kwh_helpers.check_resource_status(resource_id)
        assert_equals(status, 'not_validated')

    @raises(AttributeError)
    def test_check_validation_admin(self):
        mock_pylons()
        dataset = create_dataset()
        resource_id = dataset['id']
        validator = kwh_helpers.check_validation_admin(resource_id)
        assert_equals(validator, 0)

    def test_keyword_list(self):
        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        toolkit.get_action('keyword_create')(
            context,
            {'name': 'test'}
        )

        vocab_list = kwh_helpers.keyword_list()

        assert_equals(len(vocab_list), 1)

    @monkey_patch(Dashboard, 'add_to_index', mock.Mock())
    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    @monkey_patch(Visualization, 'add_to_index', mock.Mock())
    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_dashboard_research_questions(self):
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
            schema='',
            validation_options='',
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts',
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
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
            }
        }
        rsc_view = create_actions.resource_view_create(context, data_dict)

        data_dict1 = {
          'name': 'theme-name',
          'title': 'Test title',
          'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict1)

        data_dict2 = {
            'name': 'sub-theme-name',
            'title': 'Test sub-theme',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict2)

        data_dict3 = {
            'name': 'rq-name',
            'title': 'Test title',
            'content': 'Research question?',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id')
        }
        rq = create_actions.research_question_create(context, data_dict3)

        resource_view_id = rsc_view['id']
        research_question_id = rq['id']
        indicators = [{
                        "resource_view": rsc_view,
                        "research_question": research_question_id,
                        "resource_view_id": resource_view_id,
                        "order": 1,
                        "size": "small"
                        }]
        json_indicators = json.dumps(indicators)

        data_dict4 = {
            'name': 'internal-dashboard',
            'research_question_1': research_question_id,
            'title': 'Internal Dashboard',
            'visualization_1': resource_view_id,
            'source': '',
            'description': 'Dashboard description',
            'type': 'internal',
            'indicators': json_indicators,
            'size_1': 'small',
            'save': ''

        }
        dashboard = create_actions.dashboard_create(context, data_dict4)
        dashbourd_indicators = dashboard.get('indicators')
        dash_indicators = json.loads(dashbourd_indicators)
        dashboard['indicators'] = dash_indicators

        drq = kwh_helpers.dashboard_research_questions(context, dashboard)

        assert_equals(
          drq[0].get('id'),
          dashboard.get('indicators')[0].get('research_question')
        )

    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    @monkey_patch(Visualization, 'add_to_index', mock.Mock())
    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_add_rqs_to_dataset(self):
        Dataset.read_from_hdx.return_value = ""
        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts',
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
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
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict1 = {
            'name': 'sub-theme-name',
            'title': 'Test sub-theme',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict1)

        data_dict2 = {
            'name': 'rq-name',
            'title': 'Test title',
            'content': 'Research question?',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id')
        }
        rq = create_actions.research_question_create(context, data_dict2)

        data_dict3 = {
            'resource_id': resource.get('id'),
            'title': 'Visualization title',
            'chart_subtitle': 'Visualization subtitle',
            'chart_description': 'Visualization description',
            'view_type': 'chart',
            'color': '#00B398',
            'data_format': '',
            'show_legend': 'true',
            'y_tick_format': '',
            'y_label': '',
            'filters': '[]',
            'x_text_rotate': u'0',
            'show_labels': 'true',
            'chart_padding_bottom': u'',
            'dynamic_reference_factor': u'',
            'x_axis': u'John',
            'y_from_zero': 'true',
            'dynamic_reference_type': u'',
            'type': u'line',
            'dynamic_reference_label': u'',
            'sort': u'default',
            'research_questions': rq.get('name')
        }
        rsc_view = create_actions.resource_view_create(context, data_dict3)

        assert_equals(rsc_view.get('title'), data_dict3['title'])

    @monkey_patch(ResearchQuestion, 'add_to_index', mock.Mock())
    @monkey_patch(Visualization, 'add_to_index', mock.Mock())
    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_update_rqs_in_dataset(self):
        Dataset.read_from_hdx.return_value = ""
        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts',
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
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
            'name': 'theme-name',
            'title': 'Test title',
            'description': 'Test description'
        }
        theme = create_actions.theme_create(context, data_dict)

        data_dict1 = {
            'name': 'sub-theme-name',
            'title': 'Test sub-theme',
            'description': 'Test description',
            'theme': theme.get('id')
        }
        sub_theme = create_actions.sub_theme_create(context, data_dict1)

        data_dict2 = {
            'name': 'rq1-name',
            'title': 'Test1 title',
            'content': 'Research question?',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id')
        }
        rq1 = create_actions.research_question_create(context, data_dict2)

        data_dict3 = {
            'name': 'rq2-name',
            'title': 'Test2 title',
            'content': 'Research question2',
            'theme': theme.get('id'),
            'sub_theme': sub_theme.get('id')
        }
        rq2 = create_actions.research_question_create(context, data_dict3)

        data_dict4 = {
            'resource_id': resource.get('id'),
            'title': 'Visualization title',
            'chart_subtitle': 'Visualization subtitle',
            'chart_description': 'Visualization description',
            'view_type': 'chart',
            'color': '#00B398',
            'data_format': '',
            'show_legend': 'true',
            'y_tick_format': '',
            'y_label': '',
            'filters': '[]',
            'x_text_rotate': u'0',
            'show_labels': 'true',
            'chart_padding_bottom': u'',
            'dynamic_reference_factor': u'',
            'x_axis': u'John',
            'y_from_zero': 'true',
            'dynamic_reference_type': u'',
            'type': u'line',
            'dynamic_reference_label': u'',
            'sort': u'default',
            'research_questions': rq1.get('name')
        }
        rsc_view = create_actions.resource_view_create(context, data_dict4)

        data_dict5 = {
            'id': rsc_view.get('id'),
            'resource_id': resource.get('id'),
            'title': 'Visualization title',
            'chart_subtitle': 'Visualization subtitle',
            'chart_description': 'Visualization description',
            'view_type': 'chart',
            'color': '#00B398',
            'data_format': '',
            'show_legend': 'true',
            'y_tick_format': '',
            'y_label': '',
            'filters': '[]',
            'x_text_rotate': u'0',
            'show_labels': 'true',
            'chart_padding_bottom': u'',
            'dynamic_reference_factor': u'',
            'x_axis': u'John',
            'y_from_zero': 'true',
            'dynamic_reference_type': u'',
            'type': u'line',
            'dynamic_reference_label': u'',
            'sort': u'default',
            'research_questions': rq2.get('name')
        }
        rsc_view_update = update_actions.resource_view_update(
          context,
          data_dict5
        )

        assert_equals(
          rsc_view_update['__extras'].get('research_questions'),
          data_dict5['research_questions']
        )

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_remove_rqs_from_dataset(self):
        Dataset.read_from_hdx.return_value = ""
        dataset = create_dataset()
        resource = factories.Resource(
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts',
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )

        user = factories.Sysadmin()
        context = {
            'user': user.get('name'),
            'auth_user_obj': User(user.get('id')),
            'ignore_auth': True,
            'model': model,
            'session': model.Session
        }

        rsc_view = {
          '__extras': {
            'color': '#00B398',
            'y_label': '',
            'data_format': '',
            'show_legend': 'true',
            'dynamic_reference_type': '',
            'filters': '[]',
            'x_text_rotate': '0',
            'show_labels': 'true',
            'chart_padding_bottom': '',
            'dynamic_reference_factor': '',
            'x_axis': 'John',
            'chart_subtitle': 'subtitle1',
            'y_tick_format': '',
            'id': '854e6190-f2a1-4854-80a2-51d38e9c5c81',
            'type': 'line',
            'dynamic_reference_label': '',
            'sort': 'default',
            'research_questions': 'rq1',
            'chart_description': '   not available',
            'y_from_zero': 'true'
          },
          'description': None,
          'title': 'title1',
          'resource_id': resource.get('id'),
          'view_type': 'chart',
          'id': '854e6190-f2a1-4854-80a2-51d38e9c5c81',
          'package_id': dataset['id']
        }
        h_rm_rqs = kwh_helpers.remove_rqs_from_dataset(rsc_view)

        assert_equals(h_rm_rqs.get('message'), 'OK')

    def test_get_all_users(self):
        user_dict = {
            'name': 'knowledgehub-test',
            'email': 'test@company.com',
            'password': 'knowledgehub',
            'fullname': 'Knowledgehub Test'
        }
        toolkit.get_action('user_create')(
            get_context(),
            user_dict
        )

        users = kwh_helpers.get_all_users()

        assert_equals(len(users), 1)

    def test_shared_with_users_notification(self):
        class Editor:
            def __init__(self, name, fullname):
                self.name = name
                self.fullname = fullname

        user_dict = {
            'name': 'knowledgehub-test',
            'email': 'test@company.com',
            'password': 'knowledgehub',
            'fullname': 'Knowledgehub Test'
        }
        user = toolkit.get_action('user_create')(
            get_context(),
            user_dict
        )
        users = [user['name']]

        editor = Editor('john', 'John Smith')

        dataset = create_dataset()

        kwh_helpers.shared_with_users_notification(
            editor,
            users,
            dataset,
            kwh_helpers.Entity.Dataset,
            kwh_helpers.Permission.Granted
        )

        data_dict = {
            'name': 'internal-dashboard',
            'title': 'Internal Dashboard',
            'description': 'Dashboard description',
            'type': 'internal'
        }
        dashboard = create_actions.dashboard_create(get_context(), data_dict)

        kwh_helpers.shared_with_users_notification(
            editor,
            users,
            dashboard,
            kwh_helpers.Entity.Dashboard,
            kwh_helpers.Permission.Granted
        )

        notifications = toolkit.get_action('notification_list')(
            get_context(), {}
        )

        assert_equals(len(notifications), 2)

    def test_resource_validation_notification(self):
        class Editor:
            def __init__(self, name, fullname):
                self.name = name
                self.fullname = fullname

    
        user_dict = {
            'name': 'knowledgehub-test',
            'email': 'test@company.com',
            'password': 'knowledgehub',
            'fullname': 'Knowledgehub Test'
        }
        user = toolkit.get_action('user_create')(
            get_context(),
            user_dict
        )

        editor = Editor('john', 'John Smith')

        dataset = create_dataset()
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts',
            date_range_start='1',
            date_range_end='2',
            process_status='3',
            identifiability='4',
            hxl_ated='No',
            file_type='Microdata'
        )
        resource['admin'] = user['name']
        kwh_helpers.resource_validation_notification(
            editor,
            resource,
            kwh_helpers.Entity.Resource
        )

        notifications = toolkit.get_action('notification_list')(
            get_context(), {}
        )

        assert_equals(len(notifications), 2)

    def test_get_members(self):
        ctx = get_context()
        grp = toolkit.get_action('group_create')({
            'ignore_auth': True,
            'user': ctx['user']
        }, {
            'title': 'Group Two',
            'name': 'group-two'
        })

        toolkit.get_action('group_member_create')({
            'ignore_auth': True,
            'user': ctx['user'],
        }, {
            'id': grp['id'],
            'username': ctx['user'],
            'role': 'member',
        })

        members = kwh_helpers.get_members({
            'ignore_auth': True,
        }, grp['id'])

        assert_true(members is not None)
        assert_equals(len(members), 1)

    def test_notification_broadcast(self):
        ctx = get_context()
        grp = toolkit.get_action('group_create')({
            'ignore_auth': True,
            'user': ctx['user']
        }, {
            'title': 'Group Notifications',
            'name': 'group-notifications'
        })

        toolkit.get_action('group_member_create')({
            'ignore_auth': True,
            'user': ctx['user'],
        }, {
            'id': grp['id'],
            'username': ctx['user'],
            'role': 'member',
        })

        kwh_helpers.notification_broadcast({
            'ignore_auth': True,
        }, {
            'title': 'Test Notification 5',
            'description': 'Test Desc',
        }, [grp['id']])

        notifications = toolkit.get_action('notification_list')(ctx, {})

        assert_true(notifications is not None)
        assert_equals(notifications.get('count'), 1)

    @monkey_patch(Dataset, 'read_from_hdx', mock.Mock())
    def test_check_if_dataset_is_on_hdx(self):
        dataset = create_dataset()
        dataset['license_id'] = 'cc-by'
        dataset['private'] = True
        dataset['dataset_source'] = 'knowledgehub'
        dataset['dataset_date'] = '2020-03-11 14:37:05.887534'
        dataset['data_update_frequency'] = -1
        dataset['methodology'] = 'http://www.opendefinition.org/licenses/cc-by'
        dataset['num_resources'] = 1
        dataset['url'] = None

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

        exists = kwh_helpers.check_if_dataset_is_on_hdx(dataset['name'])
        assert_equals(exists, True)

    def test_get_comments_count(self):
        model.Session.query(CommentsRefStats).delete()
        stats = CommentsRefStats(ref='ref-0', comment_count=42)
        stats.save()

        count = kwh_helpers.get_comments_count('ref-0')
        assert_equals(count, 42)

    @monkey_patch(toolkit, 'get_action', mock.Mock())
    def test_tag_mentions(self):

        def resolve_mentions(resolved):

            def _mock_resolve_mentions(*args, **kwargs):
                return resolved

            return _mock_resolve_mentions

        toolkit.get_action.side_effect = lambda n: resolve_mentions({
            'user-1': {
                'value': 'user-1',
                'label': 'User 1',
                'link': '/users/user-1',
            },
            'organization-a': {
                'label': 'Organization A',
                'link': '/organizations/organization-a',
            }
        })

        tagged_text, mentions = kwh_helpers.tag_mentions(
            'Some mention of @user-1 and @organization-a but not @user-2')

        assert_equals(
            tagged_text,
            'Some mention of [@User 1](/users/user-1) and ' +
            '[@Organization A](/organizations/organization-a) but not @user-2'
        )
        assert_equals(len(mentions), 2)

    def test_generate_ref_type_url(self):
        url_post = kwh_helpers.generate_ref_type_url('post', 'post-1')
        assert_true(url_post is not None)
        dataset_url = kwh_helpers.generate_ref_type_url('dataset', 'dataset-1')
        assert_equals(dataset_url, '/dataset/dataset-1')

    @monkey_patch(kwh_helpers, 'request', mock.MagicMock())
    def test_log_request(self):

        req_audit_service_mock = mock.MagicMock()
        request_audit.get_request_audit.return_value = req_audit_service_mock

        request = kwh_helpers.request
        request.path = '/test/path'
        request.environ = {}

        kwh_helpers.log_request()

        from time import sleep
        sleep(1)

        request_audit.get_request_audit().shutdown()

        count, items = RequestAudit.get_all(
            query=None,
            start_time=None,
            end_time=None,
            offset=0,
            limit=10,
        )

        assert_equals(count, 1)


    def test_ignore_path(self):

        result = kwh_helpers._ignore_path('lala.jpeg')
        assert_equals(result, True)


    def test_get_datasets(self):
        res = kwh_helpers.get_datasets()
        assert_equals(len(res), 5)

    

    def test_get_searched_rqs(self):

        res = kwh_helpers.get_searched_rqs("rq")
        assert_equals(len(res), 8)

    def test_get_searched_visuals(self):

        res = kwh_helpers.get_searched_visuals("vis")
        assert_equals(len(res), 8)

    # def test_calculate_time_passed(self):
    #     time = kwh_helpers.calculate_time_passed("2019-07-02T07:59:27.609774")
    #     assert_equals(time, '1 year, 22 days ago')
    
    def test_get_active_tab(self):
        res = kwh_helpers.get_active_tab()
        assert_equals(res, 'package')

    def test_get_sort(self):
        res = kwh_helpers._get_sort()
        assert_equals(res, '')


    # def test_get_tab_url(self):

    #     res = kwh_helpers.get_tab_url('research_question')
    #     assert_equals(res, 0)

    def test_get_facets(self):

        res = kwh_helpers._get_facets()
        assert_equals(res, [])