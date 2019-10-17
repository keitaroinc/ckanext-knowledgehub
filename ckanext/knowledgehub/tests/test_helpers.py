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
from ckanext.knowledgehub import helpers as kwh_helpers
from ckanext.knowledgehub.logic.action import create as create_actions
from ckanext.knowledgehub.logic.action import get as get_actions
from ckanext.knowledgehub.tests.helpers import (User,
                                                create_dataset,
                                                mock_pylons)
from ckanext.datastore.logic.action import datastore_create
from ckanext.datastore.logic.action import datastore_search

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

        if not plugins.plugin_loaded('knowledgehub'):
            plugins.load('knowledgehub')
        if not plugins.plugin_loaded('datastore'):
            plugins.load('datastore')
        if not plugins.plugin_loaded('datapusher'):
            plugins.load('datapusher')

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

        assert_equals(len(chart_types), 12)

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
        data_formats = kwh_helpers.get_data_formats()

        assert_equals(len(data_formats), 14)

    def test_dump_json(self):
        arr = ['foo', {'bar': ('baz', None, 1.0, 2)}]
        json_str = kwh_helpers.dump_json(arr)

        assert_equals(isinstance(json_str, str), True)

    def test_get_last_visuals(self):
        dataset = create_dataset()
        resource = factories.Resource(
            schema='',
            validation_options='',
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

        last_visuals = kwh_helpers.get_last_visuals()

        assert_equals(len(last_visuals), 1)

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
            'title': 'Internal Dashboard',
            'description': 'Dashboard description',
            'type': 'internal'
        }
        dashboard = create_actions.dashboard_create(context, data_dict)

        dashboards = kwh_helpers.get_rqs_dashboards('Test')

        assert_equals(len(dashboards), 0)

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

    def test_resource_feedback_count(self):
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
            url='https://jsonplaceholder.typicode.com/posts'
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
            'title': 'Internal Dashboard',
            'description': 'Dashboard description',
            'type': 'internal'
        }
        dashboard = create_actions.dashboard_create(context, data_dict)

        dashboards = kwh_helpers.get_dashboards()

        assert_equals(len(dashboards), 1)

    def test_remove_space_for_url(self):
        url = 'http://host:port/lang/data set'

        new_url = kwh_helpers.remove_space_for_url(url)
        assert_equals(new_url, 'http://host:port/lang/data-set')


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
        titles = kwh_helpers.get_rq_options(True)

        assert_equals(len(titles), 1)

    def test_get_rq_ids(self):
        dataset = create_dataset()
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'
        )
        rqs = kwh_helpers.get_rq_ids(resource['id'])
        assert_equals(len(rqs), 2)

   
    def test_get_geojson_resources(self):

        dataset = create_dataset()
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            format='geojson'
        )
        resources = kwh_helpers.get_geojson_resources()
        assert_equals(len(resources), 1)

    def test_get_rq_titles_from_res(self):

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

        rq1 = create_actions.research_question_create(context, data_dict)
        dataset = create_dataset(
            research_question = rq1['id']
            
        )
        resource = factories.Resource(
            schema='',
            validation_options='',
            package_id=dataset['id'],
            url='https://jsonplaceholder.typicode.com/posts'

        )

        titles = kwh_helpers.get_rq_titles_from_res(resource['id'])
        assert_equals(len(titles), 1)

    def test_resource_view_get_fields(self):
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
        fields = kwh_helpers.resource_view_get_fields(resource)
        assert_equals(len(fields), 2)


    def test_get_filter_values(self):
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

        fil_vals = kwh_helpers.get_filter_values(resource['id'], "value", [])
        assert_equals(len(fil_vals), 7)

    def test_get_resource_columns(self):
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

        columns = kwh_helpers.get_resource_columns(resource.get('id'))
        assert_equals(len(columns), 1)

    def test_get_resource_data(self):
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
        res_data = kwh_helpers.get_resource_data(sql_str)
        
        assert_equals(len(res_data), 7)
    
    
    def test_get_geojson_properties(self):

        url = "https://www.grandconcourse.ca/map/data/GCPoints.geojson"
        res = kwh_helpers.get_geojson_properties(url)
        assert_equals(len(res), 26)

    # def test_get_map_data(self):
    #     dataset = create_dataset()
    #     data = {
    #         "url" : "https://www.grandconcourse.ca/map/data/GCPoints.geojson",
    #         "force": True
    #     }
    #     resource = factories.Resource(
    #         schema='',
    #         validation_options='',
    #         package_id=dataset['id'],
    #         datastore_active=True,
    #         format='geojson'

    #     )
    #     data['resource_id'] = resource['id']

    #     map_key_field = "Name"
    #     data_key_field = "features"
    #     data_value_field = "20"
    #     from_where = ""
    #     url = "https://www.grandconcourse.ca/map/data/GCPoints.geojson"

    #     helpers.call_action('datastore_create', **data)
    #     res = kwh_helpers.get_map_data(url, map_key_field, data_key_field, data_value_field, from_where)
    #     assert_equals(res, "")