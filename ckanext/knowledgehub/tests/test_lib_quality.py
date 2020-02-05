from mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from random import randint

from ckan.tests import helpers
import ckan.plugins.toolkit as toolkit
from ckanext.knowledgehub.lib.quality import (
    LazyStreamingList,
    DataQualityMetrics,
    Completeness,
    Uniqueness,
    Timeliness,
    Accuracy,
    Consistency,
    Validity,
)
from ckanext.knowledgehub.model.data_quality import DataQualityMetrics as DataQualityMetricsModel
from ckanext.knowledgehub.lib.util import monkey_patch

from nose.tools import (
    assert_true,
    assert_equals,
    raises,
)


class TestLazyStreamList:

    def test_iterator(self):
        data = [i for i in range(0, 134)]
        calls = {'fetch_page_calls': 0}

        def _fetch_page(page, page_size):
            calls['fetch_page_calls'] += 1
            return {
                'total': len(data),
                'records': data[page*page_size: min([(page +1)*page_size, len(data)])]
            }

        lazy_list = LazyStreamingList(_fetch_page, 10)

        count = 0
        for result in lazy_list:
            assert_equals(count, result)
            count += 1
        
        assert_equals(count, len(data))
        assert_equals(calls['fetch_page_calls'], 14)


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
        assert_equals(2, quality_metrics.calculate_metrics_for_resource.call_count)
        quality_metrics.calculate_cumulative_metrics.assert_called_once_with(
            'test-dataset',
            [{
                'id': 'rc-1', 
                'data_quality_settings': {
                    'completeness':{
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
            },{
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
            'completeness':{
                'value': 10.0,
            }
        },{
            'completeness': {
                'value': 20.4,
            }
        }]
        quality_metrics.calculate_cumulative_metrics('000-1', resources, results)


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
            'completeness':{
                'value': 10.0,
            }
        },{
            'completeness': {
                'value': 20.4,
            }
        }]
        quality_metrics.calculate_cumulative_metrics('000-1', resources, results)


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
            'fields': [{'id': 'col1', 'type': 'text'}, {'id': 'col2', 'type': 'int'}],
            'records': [{
                'col1': 'record-%d' % i if i%2 else '' if i%3 else ' '*i,
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
        },{
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
            'fields':[{
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
        },{
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
        assert_equals(report.get('value'), '+' + str(timedelta(seconds=round((3600*(5+10))/(5+7)))))
        assert_equals(report.get('records'), 12)


class TestValidity():

    @monkey_patch(toolkit, 'get_action', Mock())
    def test_calculate_metric(self):
        validity = Validity()
        data = [
            ['col1', 'col2'],
        ] + [ ['record+%d' % i, i] for i in range(0, 10)]
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
                'records': [{'col1': row[0], 'col2': row[1]} for row in data[1:]]
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
        },{
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
                'col1': str(randint(1, 10)) + ',' + str(randint(100,999)),
                'col2': datetime.now().isoformat(),
                'col3': 'record-%d' % i,
            } for i in range(0, 100)]
        }
        
        for i in range(0, 30):
            data['records'][i*3+randint(0, 2)]['col1'] = str(randint(1, 1000))
            data['records'][i*3+randint(0, 2)]['col2'] = datetime.now().strftime('%Y.%m.%d')
        
        report = consistency.calculate_metric(resource, data)
        assert_true(report is not None)
        assert_equals(report.get('total'), 300)
        assert_equals(report.get('consistent'), 240)
        assert_equals(report.get('value'), 80.0)
        