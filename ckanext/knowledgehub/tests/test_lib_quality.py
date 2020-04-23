from mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile, mkdtemp
from random import randint, random

from ckan.tests import helpers
import ckan.plugins.toolkit as toolkit
import ckan.lib.uploader as uploader
import ckan.logic as logic
from ckan.common import config
from ckanext.knowledgehub.lib.quality import (
    LazyStreamingList,
    DataQualityMetrics,
    Completeness,
    Uniqueness,
    Timeliness,
    Accuracy,
    Consistency,
    Validity,
    ResourceCSVData,
    ResourceFetchData,
)
from ckanext.knowledgehub.model.data_quality import (
    DataQualityMetrics as DataQualityMetricsModel
)
from ckanext.knowledgehub.lib.util import monkey_patch

from nose.tools import (
    assert_true,
    assert_equals,
    raises,
)
import responses
import shutil
import os


class TestLazyStreamList:

    def test_iterator(self):
        data = [i for i in range(0, 134)]
        calls = {'fetch_page_calls': 0}

        def _fetch_page(page, page_size):
            calls['fetch_page_calls'] += 1
            return {
                'total': len(data),
                'records': data[
                    page * page_size: min([(page + 1) * page_size, len(data)])]
            }

        lazy_list = LazyStreamingList(_fetch_page, 10)

        count = 0
        for result in lazy_list:
            assert_equals(count, result)
            count += 1

        assert_equals(count, len(data))
        assert_equals(calls['fetch_page_calls'], 14)


class TestResourceCSVData:

    def test_initialize_resource_data(self):
        csv_data = [
            ['a', 'b', 'c'],
        ]
        csv_data += [[randint(-10, 10),
                      random(),
                      'test-%d' % i] for i in range(0, 10)]

        resource_data = ResourceCSVData(lambda: csv_data)

        assert_true(resource_data.fields is not None)
        assert_true(resource_data.column_names is not None)
        assert_equals(resource_data.total, 10)
        assert_equals(resource_data.column_names, ['a', 'b', 'c'])
        assert_equals(resource_data.fields, [
            {'id': 'a', 'type': 'numeric'},
            {'id': 'b', 'type': 'numeric'},
            {'id': 'c', 'type': 'text'}])

    def test_initialize_resource_data_columns_with_same_name(self):
        csv_data = [
            ['a', 'b', 'a'],
        ]
        csv_data += [[randint(-10, 10),
                      random(),
                      'test-%d' % i] for i in range(0, 10)]

        resource_data = ResourceCSVData(lambda: csv_data)

        assert_true(resource_data.fields is not None)
        assert_true(resource_data.column_names is not None)
        assert_equals(resource_data.total, 10)
        assert_equals(resource_data.column_names, ['a_1', 'b', 'a_2'])
        assert_equals(resource_data.fields, [
            {'id': 'a_1', 'type': 'numeric'},
            {'id': 'b', 'type': 'numeric'},
            {'id': 'a_2', 'type': 'text'}])

    def test_fetch_data(self):
        csv_data = [
            ['a', 'b', 'c'],
        ]
        csv_data += [[randint(-10, 10),
                      random(),
                      'test-%d' % i] for i in range(0, 10)]

        resource_data = ResourceCSVData(lambda: csv_data)

        assert_true(resource_data.fields is not None)
        assert_true(resource_data.column_names is not None)
        assert_equals(resource_data.total, 10)

        page = resource_data.fetch_page(0, 3)
        assert_true(page is not None)
        assert_equals(page.get('total'), 10)
        assert_true(page.get('records') is not None)
        assert_equals(len(page.get('records')), 3)

        assert_equals([c['a'] for c in page['records']],
                      [r[0] for r in csv_data[1:4]])
        assert_equals([c['b'] for c in page['records']],
                      [r[1] for r in csv_data[1:4]])
        assert_equals([c['c'] for c in page['records']],
                      [r[2] for r in csv_data[1:4]])

        # Next page, again 3
        page = resource_data.fetch_page(1, 3)
        assert_true(page is not None)
        assert_equals(page.get('total'), 10)
        assert_true(page.get('records') is not None)
        assert_equals(len(page.get('records')), 3)

        # Next page again 3
        page = resource_data.fetch_page(2, 3)
        assert_true(page is not None)
        assert_equals(page.get('total'), 10)
        assert_true(page.get('records') is not None)
        assert_equals(len(page.get('records')), 3)

        # Final page, 1 record
        page = resource_data.fetch_page(3, 3)
        assert_true(page is not None)
        assert_equals(page.get('total'), 10)
        assert_true(page.get('records') is not None)
        assert_equals(len(page.get('records')), 1)


class TestResourceFetchData:

    @monkey_patch(toolkit, 'get_action', Mock())
    def test_fetch_page_datastore(self):

        res_page = {
            'total': 10,
            'records': [{'a': i} for i in range(0, 3)],
            'fields': [{'id': 'a', 'type': 'numeric'}],
        }

        def _mock_datastore_search(*args, **kwargs):
            return res_page

        toolkit.get_action.return_value = _mock_datastore_search

        resource = {
            'id': 'rc-1',
        }

        fetch_data = ResourceFetchData(resource)

        page = fetch_data.fetch_page(0, 3)
        assert_equals(page, res_page)

        toolkit.get_action.assert_called_once_with('datastore_search')

    def test_call_as_callable(self):
        resource = {}

        fetch_data_callable = ResourceFetchData(resource)

        fetch_data_callable.fetch_page = Mock()

        fetch_data_callable(1, 14)

        fetch_data_callable.fetch_page.assert_called_once_with(1, 14)

    @monkey_patch(toolkit, 'get_action', Mock())
    @responses.activate
    def test_fetch_page_remote_url(self):
        datastore_search_mock = Mock()
        toolkit.get_action.return_value = datastore_search_mock

        def _raise_not_found(*args, **kwargs):
            raise logic.NotFound('Not found')

        datastore_search_mock.side_effect = _raise_not_found

        rc1_csv = '\n'.join([
            'a,b,a,a,b,c',
            '1.0,val1,2,val10,3,4',
            '1.1,val2,20,val20,30,40',
            '1.2,val3,30,val30,40,50',
            '1.3,val4,40,val40,50,60',
        ])

        responses.add(responses.GET,
                      url='http://example.com/downloads/rc-1.csv',
                      body=rc1_csv,
                      status=200)

        fetch_data = ResourceFetchData({
            'id': 'rc-1',
            'url': 'http://example.com/downloads/rc-1.csv',
        })

        page = fetch_data(0, 3)

        assert_true(page is not None)
        assert_equals(page.get('total'), 4)
        assert_equals(page.get('fields'), [
            {'id': 'a_1', 'type': 'numeric'},
            {'id': 'b_1', 'type': 'text'},
            {'id': 'a_2', 'type': 'numeric'},
            {'id': 'a_3', 'type': 'text'},
            {'id': 'b_2', 'type': 'numeric'},
            {'id': 'c', 'type': 'numeric'},
        ])

    def test_fetch_page_ckan_resource_local_worker(self):
        tmpdir = None
        old_storage_path = config.get('ckan.storage_path')
        try:
            tmpdir = mkdtemp()
            resource_id = 'aaabbbrc1'
            resources_dir = os.path.join(tmpdir,
                                         'resources',
                                         resource_id[0:3],
                                         resource_id[3:6])
            os.makedirs(resources_dir)

            @monkey_patch(uploader, '_storage_path', tmpdir)
            def _run_fetch_data():
                with open(os.path.join(resources_dir,
                                       resource_id[6:]), 'w') as f:
                    data = [
                        ['a', 'b', 'c'],
                        ['val1', '1', '1.0'],
                        ['val2', '2', '2.0'],
                        ['val3', '3', '3.0'],
                        ['val4', '4', '4.0'],
                    ]
                    for row in data:
                        f.write(','.join(row) + '\n')

                config['ckan.storage_path'] = tmpdir
                resource = {
                    'id': resource_id,
                    'url_type': 'upload',
                    'url': 'http://example.com/download/{}.csv'.format(
                        resource_id
                    ),
                }

                fetch_data = ResourceFetchData(resource)

                page = fetch_data.fetch_page(1, 2)
                assert_true(page is not None)
                assert_equals(page.get('total'), 4)
                assert_equals(page.get('records'), [
                    {'a': 'val3', 'b': '3', 'c': '3.0'},
                    {'a': 'val4', 'b': '4', 'c': '4.0'},
                ])
                assert_equals(page.get('fields'), [
                    {'id': 'a', 'type': 'text'},
                    {'id': 'b', 'type': 'numeric'},
                    {'id': 'c', 'type': 'numeric'},
                ])

            _run_fetch_data()

        finally:
            config['ckan.storage_path'] = old_storage_path
            if tmpdir:
                shutil.rmtree(tmpdir)


class TestDataQualityMetrics(helpers.FunctionalTestBase):

    def test_calculate_metrics_for_dataset(self):
        metric = MagicMock()
        quality_metrics = DataQualityMetrics([metric])
        quality_metrics._fetch_dataset = Mock()
        quality_metrics.calculate_metrics_for_resource = Mock()
        quality_metrics.calculate_cumulative_metrics = Mock()

        metric.name = 'completeness'

        quality_metrics._fetch_dataset.return_value = {
            'id': 'test-dataset',
            'resources': [{
                'id': 'rc-1',
                'dq_completeness_setting': 'setting-value',
            }, {
                'id': 'rc-2'
            }],
        }

        quality_metrics.calculate_metrics_for_resource.return_value = {
            'value': 10.8,
        }

        quality_metrics.calculate_metrics_for_dataset('test-dataset')

        quality_metrics._fetch_dataset.assert_called_once_with('test-dataset')
        assert_equals(
            2,
            quality_metrics.calculate_metrics_for_resource.call_count
        )
        quality_metrics.calculate_cumulative_metrics.assert_called_once_with(
            'test-dataset',
            [{
                'id': 'rc-1',
                'data_quality_settings': {
                    'completeness': {
                        'setting': 'setting-value'
                    }
                },
                'dq_completeness_setting': 'setting-value',
                }, {
                    'id': 'rc-2',
                    'data_quality_settings': {},
            }],
            [{
                'value': 10.8,
            }, {
                'value': 10.8,
            }]
        )

    def test_calculate_metrics_for_resource(self):
        metric = MagicMock()
        metric.name = 'completeness'
        quality_metrics = DataQualityMetrics([metric])

        quality_metrics._get_metrics_record = Mock()
        quality_metrics._new_metrics_record = Mock()

        metric.calculate_metric.return_value = {
            'value': 10.6,
        }

        dq = DataQualityMetricsModel(
            type='resource',
            id='000-1',
            resource_last_modified=datetime.now() - timedelta(hours=1))

        dq.save = Mock()

        quality_metrics._get_metrics_record.return_value = dq
        quality_metrics._new_metrics_record.return_value = dq

        quality_metrics._fetch_resource_data = Mock()
        quality_metrics._fetch_resource_data.return_value = {
            'total': 120,
            'records': [{} for _ in range(0, 120)],
        }

        resource = {
            'id': 'rc-1',
            'last_modified': datetime.now().isoformat(),
        }

        results = quality_metrics.calculate_metrics_for_resource(resource)
        assert_true(results is not None)
        assert_equals(len(results), 1)

        dq.save.assert_called_once()
        metric.calculate_metric.assert_called_once()
        quality_metrics._fetch_resource_data.assert_called_once_with(resource)
        assert_equals(dq.completeness, 10.6)
        assert_true(dq.metrics is not None)

    def test_calculate_metrics_for_resource_cached_result(self):
        metric = MagicMock()
        metric.name = 'completeness'
        quality_metrics = DataQualityMetrics([metric])

        quality_metrics._get_metrics_record = Mock()

        metric.calculate_metric.return_value = {
            'value': 10.6,
        }

        dq = DataQualityMetricsModel(
            type='resource',
            id='000-1',
            resource_last_modified=datetime.now() + timedelta(hours=1),
            completeness=20.7,
            metrics={
                'completeness': {
                    'value': 20.7,
                }
            }
        )

        dq.save = Mock()

        quality_metrics._get_metrics_record.return_value = dq

        quality_metrics._fetch_resource_data = Mock()
        quality_metrics._fetch_resource_data.return_value = {
            'total': 120,
            'records': [{} for _ in range(0, 120)],
        }

        resource = {
            'id': 'rc-1',
            'last_modified': datetime.now().isoformat(),
        }

        results = quality_metrics.calculate_metrics_for_resource(resource)
        assert_true(results is not None)
        assert_equals(len(results), 1)

        dq.save.assert_called_once()
        assert_equals(metric.calculate_metric.call_count, 0)
        assert_equals(quality_metrics._fetch_resource_data.call_count, 0)
        assert_equals(dq.completeness, 20.7)
        assert_true(dq.metrics is not None)

    def test_calculate_metrics_for_resource_cached_error(self):
        metric = MagicMock()
        metric.name = 'completeness'
        quality_metrics = DataQualityMetrics([metric])

        quality_metrics._get_metrics_record = Mock()
        quality_metrics._new_metrics_record = Mock()

        metric.calculate_metric.return_value = {
            'value': 10.6,
        }

        dq = DataQualityMetricsModel(
            type='resource',
            id='000-1',
            completeness=15.5,
            resource_last_modified=datetime.now() - timedelta(hours=1),
            metrics={
                'completeness': {
                    'failed': True,  # previous attempt to calculate failed
                    'error': 'Test error',
                }
            }
        )

        dq.save = Mock()

        quality_metrics._get_metrics_record.return_value = dq
        quality_metrics._new_metrics_record.return_value = dq

        quality_metrics._fetch_resource_data = Mock()
        quality_metrics._fetch_resource_data.return_value = {
            'total': 120,
            'records': [{} for _ in range(0, 120)],
        }

        resource = {
            'id': 'rc-1',
            'last_modified': datetime.now().isoformat(),
        }

        results = quality_metrics.calculate_metrics_for_resource(resource)
        assert_true(results is not None)
        assert_equals(len(results), 1)

        dq.save.assert_called_once()
        metric.calculate_metric.assert_called_once()
        quality_metrics._fetch_resource_data.assert_called_once_with(resource)
        assert_equals(dq.completeness, 10.6)
        assert_true(dq.metrics is not None)

    def test_calculate_metrics_for_resource_cached_manual(self):
        metric = MagicMock()
        metric.name = 'completeness'
        quality_metrics = DataQualityMetrics([metric])

        quality_metrics._get_metrics_record = Mock()

        metric.calculate_metric.return_value = {
            'value': 10.6,
        }

        dq = DataQualityMetricsModel(
            type='resource',
            id='000-1',
            resource_last_modified=datetime.now() + timedelta(hours=1),
            completeness=33.6,
            metrics={
                'completeness': {
                    'manual': True,
                    'value': 33.6,
                }
            }
        )

        dq.save = Mock()

        quality_metrics._get_metrics_record.return_value = dq

        quality_metrics._fetch_resource_data = Mock()
        quality_metrics._fetch_resource_data.return_value = {
            'total': 120,
            'records': [{} for _ in range(0, 120)],
        }

        resource = {
            'id': 'rc-1',
            'last_modified': datetime.now().isoformat(),
        }

        results = quality_metrics.calculate_metrics_for_resource(resource)
        assert_true(results is not None)
        assert_equals(len(results), 1)

        dq.save.assert_called_once()
        assert_equals(metric.calculate_metric.call_count, 0)
        assert_equals(quality_metrics._fetch_resource_data.call_count, 0)
        assert_equals(dq.completeness, 33.6)
        assert_true(dq.metrics is not None)

    def test_calculate_cumulative_metrics(self):
        metric = MagicMock()
        metric.name = 'completeness'
        quality_metrics = DataQualityMetrics([metric])

        quality_metrics._get_metrics_record = Mock()
        quality_metrics._new_metrics_record = Mock()

        metric.calculate_cumulative_metric.return_value = {
            'value': 10.6,
        }

        dq = DataQualityMetricsModel(
            type='package',
            id='000-1',
            resource_last_modified=datetime.now() - timedelta(hours=1),
            completeness=33.6,
            metrics={}
        )

        dq.save = Mock()

        quality_metrics._get_metrics_record.return_value = dq
        quality_metrics._new_metrics_record.return_value = dq

        resources = [{
            'id': 'resource-1',
        }, {
            'id': 'resource-2',
        }]
        results = [{
            'completeness': {
                'value': 10.0,
            }
        }, {
            'completeness': {
                'value': 20.4,
            }
        }]
        quality_metrics.calculate_cumulative_metrics(
            '000-1',
            resources,
            results
        )

        quality_metrics._get_metrics_record.assert_called_once()
        metric.calculate_cumulative_metric.assert_called_once_with(
            resources,
            [{
                'value': 10.0,
            }, {
                'value': 20.4,
            }]
        )
        dq.save.assert_called_once()
        assert_equals(dq.completeness, 10.6)

    def test_calculate_cumulative_metrics_manual_result(self):
        metric = MagicMock()
        metric.name = 'completeness'
        quality_metrics = DataQualityMetrics([metric])

        quality_metrics._get_metrics_record = Mock()

        metric.calculate_cumulative_metric.return_value = {
            'value': 10.6,
        }

        dq = DataQualityMetricsModel(
            type='package',
            id='000-1',
            resource_last_modified=datetime.now() - timedelta(hours=1),
            completeness=33.6,
            metrics={
                'completeness': {
                    'manual': True,
                    'value': 33.6,
                }
            }
        )

        dq.save = Mock()

        quality_metrics._get_metrics_record.return_value = dq

        resources = [{
            'id': 'resource-1',
        }, {
            'id': 'resource-2',
        }]
        results = [{
            'completeness': {
                'value': 10.0,
            }
        }, {
            'completeness': {
                'value': 20.4,
            }
        }]
        quality_metrics.calculate_cumulative_metrics(
            '000-1',
            resources,
            results
        )

        quality_metrics._get_metrics_record.assert_called_once()
        assert_equals(metric.calculate_cumulative_metric.call_count, 0)
        dq.save.assert_called_once()
        assert_equals(dq.completeness, 33.6)


class TestCompleteness():

    def test_calculate_metric(self):
        completeness = Completeness()

        resource = {
            'id': 'rc-1',
        }

        data = {
            'total': 10,
            'fields': [
                {'id': 'col1', 'type': 'text'},
                {'id': 'col2', 'type': 'int'}
            ],
            'records': [{
                'col1': 'record-%d' % i if i % 2 else '' if i % 3 else ' '*i,
                'col2': i if i % 2 else None,
            } for i in range(0, 10)]
        }

        report = completeness.calculate_metric(resource, data)
        assert_true(report is not None)
        assert_equals(report.get('total'), 20)
        assert_equals(report.get('complete'), 10)
        assert_equals(report.get('value'), 50.0)

    def test_calculate_cumulative_metric(self):
        completeness = Completeness()

        resources = [{
            'id': 'rc-1',
        }, {
            'id': 'rc-2',
        }]
        metrics = [{
            'total': 10,
            'value': 60.0,
            'complete': 6,
        }, {
            'total': 20,
            'value': 40.0,
            'complete': 8,
        }]
        report = completeness.calculate_cumulative_metric(resources, metrics)
        assert_true(report is not None)
        assert_equals(report.get('total'), 30)
        assert_equals(report.get('complete'), 14)
        assert_equals(report.get('value'), float(14)/float(30) * 100.0)


class TestUniqueness():

    def test_calculate_metric(self):
        uniq = Uniqueness()

        resource = {'id': 'rc-1'}

        col1 = ['A', 'B', 'C']*4
        col2 = [1, 2, 3, 4]*3

        data = {
            'total': 10,
            'fields': [{
                'id': 'col1',
                'type': 'text',
            }, {
                'id': 'col2',
                'type': 'int',
            }],
            'records': [{
                'col1': col1[i],
                'col2': col2[i],
            } for i in range(0, 10)]
        }

        report = uniq.calculate_metric(resource, data)
        assert_true(report is not None)
        assert_equals(report.get('total'), 20)
        assert_equals(report.get('unique'), 7)
        assert_equals(report.get('value'), 7.0/20.0 * 100.0)
        assert_equals(report.get('columns'), {
            'col1': {
                'unique': 3,
                'total': 10,
                'value': 3.0/10.0*100.0
            },
            'col2': {
                'unique': 4,
                'total': 10,
                'value': 4.0/10.0*100.0
            },
        })

    def test_calculate_cumulative_metric(self):
        uniq = Uniqueness()

        resources = [{
            'id': 'rc-1',
        }, {
            'id': 'rc-2',
        }, {
            'id': 'rc-3',
        }]

        results = [{
            'total': 10,
            'unique': 3,
            'value': 30.0,
        }, {
            'total': 20,
            'unique': 11,
            'value': 11.0/20.0*100.0,
        }, {
            'total': 50,
            'unique': 44,
            'value': 44.0/50.0*100.0,
        }]

        report = uniq.calculate_cumulative_metric(resources, results)
        assert_true(report is not None)
        assert_equals(report.get('total'), 80)
        assert_equals(report.get('unique'), 3+11+44)
        assert_equals(report.get('value'), float(3+11+44)/80.0 * 100.0)


class TestTimeliness():

    def test_calculate_metric(self):
        timeliness = Timeliness()

        resource = {
            'id': 'rc-1',
            'data_quality_settings': {
                'timeliness': {
                    'column': 'entry_date',
                }
            },
            'last_modified': datetime.now().isoformat(),
        }

        dt = datetime.now() - timedelta(hours=10)

        data = {
            'total': 10,
            'fields': [{
                'id': 'col1',
                'type': 'text',
            }, {
                'id': 'entry_date',
                'type': 'timestamp',
            }],
            'records': [{
                'col1': 'recors-%d' % i,
                'entry_date': (dt + timedelta(hours=i)).isoformat(),
            } for i in range(0, 10)]
        }

        expected_delta = sum([(10-i)*3600 for i in range(0, 10)])
        expcted_value = '+' + str(timedelta(seconds=expected_delta/10))

        report = timeliness.calculate_metric(resource, data)
        assert_true(report is not None)
        assert_equals(report.get('total'), expected_delta)
        assert_equals(report.get('value'), expcted_value)
        assert_equals(report.get('average'), expected_delta/10)
        assert_equals(report.get('records'), 10)

    def test_calculate_cumulative_metric(self):
        timeliness = Timeliness()
        resources = [{
            'id': 'rc-1',
        }, {
            'id': 'rc-1',
        }]

        results = [{
            'total': 3600*5,
            'records': 5,
            'average': 3600.0,
            'value': '+' + str(timedelta(hours=1)),
        }, {
            'total': 3600*10,
            'records': 7,
            'average': round(3600.0*10.0/7.0),
            'value': '+' + str(timedelta(seconds=round(3600.0*10.0/7.0))),
        }]

        report = timeliness.calculate_cumulative_metric(resources, results)
        assert_true(report is not None)
        assert_equals(report.get('total'), 3600*(5+10))
        assert_equals(report.get('average'), round((3600*(5+10))/(5+7)))
        assert_equals(report.get('value'),
                      '+' + str(timedelta(seconds=round((3600*(5+10))/(5+7)))))
        assert_equals(report.get('records'), 12)


class TestValidity():

    @monkey_patch(toolkit, 'get_action', Mock())
    def test_calculate_metric(self):
        validity = Validity()
        data = [
            ['col1', 'col2'],
        ] + [['record+%d' % i, i] for i in range(0, 10)]
        with NamedTemporaryFile() as data_file:
            for row in data:
                data_file.write(','.join([str(c) for c in row]) + '\n')

            data_file.flush()

            resource = {
                'id': 'rc-1',
                'url': data_file.name,
                'package_id': 'test-001',
                'format': 'csv',
                'schema': {
                    'fields': [{
                        'name': 'col1',
                        'type': 'string',
                    }, {
                        'name': 'col2',
                        'type': 'integer',
                    }]
                }
            }

            rc_data = {
                'total': 10,
                'fields': [{
                    'id': 'col1',
                    'type': 'text',
                }, {
                    'id': 'col2',
                    'type': 'int',
                }],
                'records': [
                    {'col1': row[0], 'col2': row[1]} for row in data[1:]
                ]
            }

            report = validity.calculate_metric(resource, rc_data)
            assert_true(report is not None)
            assert_equals(report.get('total'), 10)
            assert_equals(report.get('valid'), 10)
            assert_equals(report.get('value'), 100.0)

    def test_calculate_cumulative_metric(self):
        validity = Validity()

        resources = [{
            'id': 'rc-1',
        }, {
            'id': 'rc-2',
        }]

        results = [{
            'total': 100,
            'valid': 85,
            'value': 85.0
        }, {
            'total': 150,
            'valid': 35,
            'value': 35.0/150.0*100.0
        }]

        report = validity.calculate_cumulative_metric(resources, results)

        assert_true(report is not None)
        assert_equals(report.get('total'), 250)
        assert_equals(report.get('valid'), 85+35)
        assert_equals(report.get('value'), (85.0+35.0)/250.0 * 100.0)


class TestAccuracy():

    def test_calculate_metric(self):
        accuracy = Accuracy()

        resource = {
            'id': 'rc-1',
            'data_quality_settings': {
                'accuracy': {
                    'column': 'is_accurate',
                }
            }
        }

        data = {
            'total': 30,
            'fields': [{
                'id': 'col1',
                'type': 'string',
            }, {
                'id': 'is_accurate',
                'type': 'string',
            }],
            'records': [{
                'col1': 'record-%d' % i,
                'is_accurate': 'T' if i % 3 == 0 else 'F',
            } for i in range(0, 30)]
        }

        report = accuracy.calculate_metric(resource, data)
        assert_true(report is not None)
        assert_equals(report.get('total'), 30)
        assert_equals(report.get('accurate'), 10)
        assert_equals(report.get('inaccurate'), 20)
        assert_equals(report.get('value'), 10.0/30.0*100.0)

    def test_calculate_cumulative_metric(self):
        accuracy = Accuracy()

        resources = [{
            'id': 'rc-1',
        }, {
            'id': 'rc-2',
        }]

        results = [{
            'total': 30,
            'accurate': 20,
            'inaccurate': 10,
            'value': 20.0/30.0*100.0,
        }, {
            'total': 130,
            'accurate': 120,
            'inaccurate': 10,
            'value': 120.0/130.0*100.0,
        }]

        report = accuracy.calculate_cumulative_metric(resources, results)
        assert_true(report is not None)
        assert_equals(report.get('total'), 160)
        assert_equals(report.get('accurate'), 140)
        assert_equals(report.get('inaccurate'), 20)
        assert_equals(report.get('value'), 140.0/160.0*100.0)


class TestConsistency():

    def test_calculate_metric(self):
        consistency = Consistency()

        resource = {
            'id': 'rc-1',
        }

        data = {
            'total': 100,
            'fields': [{
                'id': 'col1',
                'type': 'numeric',
            }, {
                'id': 'col2',
                'type': 'timestamp',
            }, {
                'id': 'col3',
                'type': 'string',
            }],
            'records': [{
                'col1': str(randint(1, 10)) + ',' + str(randint(100, 999)),
                'col2': datetime.now().isoformat(),
                'col3': 'record-%d' % i,
            } for i in range(0, 100)]
        }

        for i in range(0, 30):
            data['records'][i*3+randint(0, 2)]['col1'] = str(randint(1, 1000))
            data['records'][i*3+randint(0, 2)]['col2'] = \
                datetime.now().strftime('%Y.%m.%d')

        report = consistency.calculate_metric(resource, data)
        assert_true(report is not None)
        assert_equals(report.get('total'), 300)
        assert_equals(report.get('consistent'), 240)
        assert_equals(report.get('value'), 80.0)
