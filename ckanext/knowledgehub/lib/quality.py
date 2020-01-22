import ckan.plugins.toolkit as toolkit
from ckanext.knowledgehub.model.data_quality import (
    DataQualityMetrics as DataQualityMetricsModel
)
from logging import getLogger
from functools import reduce
from datetime import datetime, timedelta
import dateutil


class DimensionMetric(object):

    def __init__(self, name):
        self.name = name
        self.logger = getLogger('ckanext.data_quality.%s' % self.name)

    def calculate_metric(self, resource, data):
        return {}

    def calculate_cumulative_metric(self, resources, metrics):
        return {}

    def __str__(self):
        return 'DataQualityDimension<%s>' % self.name


class DataQualityMetrics(object):

    def __init__(self, metrics=None):
        self.metrics = metrics or []
        self.logger = getLogger('ckanext.DataQualityMetrics')

    def _fetch_dataset(self, package_id):
        return toolkit.get_action('package_show')(
            {
                'ignore_auth': True,
            },
            {
                'id': package_id,
            }
        )
    
    def _data_quality_settings(self, resource):
        settings = {}
        for dimension in ['completeness', 'uniqueness', 'timeliness',
                          'validity', 'accuracy', 'consistency']:
            for key, value in resource.items():
                prefix = 'dq_%s' % dimension
                if key.startswith(prefix):
                    if settings.get(dimension) is None:
                        settings[dimension] = {}
                    setting = key[len(prefix) + 1:]
                    settings[dimension][setting] = value
        return settings

    def _fetch_resource_data(self, resource):
        # FIXME: Maybe fetch differently for different resources types?
        try:
            results = toolkit.get_action('datastore_search')(
                {
                    'ignore_auth': True,
                },
                {
                    'resource_id': resource['id'],
                    'offset': 0
                }
            )
            if results and results['total']:
                # FIXME: do this with pagination if we have too large datasets
                results = toolkit.get_action('datastore_search')(
                    {
                        'ignore_auth': True,
                    },
                    {
                        'resource_id': resource['id'],
                        'offset': 0,
                        'limit': results['total'],
                    }
                )
            return results
        except Exception as e:
            self.logger.warning('Failed to fetch data for resource %s. Error: %s', resource['id'], str(e))
            self.logger.exception(e)
            return {
                'total': 0,
                'records': [],
            }

    def _get_metrics_record(self, ref_type, ref_id):
        metrics = DataQualityMetricsModel.get(ref_type, ref_id)
        return metrics

    def calculate_metrics_for_dataset(self, package_id):
        self.logger.debug('Calculating data quality for dataset: %s',
                          package_id)
        dataset = self._fetch_dataset(package_id)
        results = []
        for resource in dataset['resources']:
            self.logger.debug('Calculating data quality for resource: %s',
                              resource['id'])
            resource['data_quality_settings'] = self._data_quality_settings(resource)
            data = self._fetch_resource_data(resource)
            result = self.calculate_metrics_for_resource(resource, data)
            if result is None:
                result = {}
            self.logger.debug('Result: %s', result)
            results.append(result)

        # calculate cumulative
        self.logger.debug('Calculating cumulative data quality metrics for %s',
                          package_id)
        self.calculate_cumulative_metrics(package_id,
                                          dataset['resources'],
                                          results)
        self.logger.info('Data Quality metrcis calculated for dataset: %s.',
                         package_id)

    def calculate_metrics_for_resource(self, resource, data):
        last_modified = datetime.strptime((resource.get('last_modified') or
                                           resource.get('created')),
                                          '%Y-%m-%dT%H:%M:%S.%f')
        self.logger.debug('Resource last modified on: %s', last_modified)
        data_quality = self._get_metrics_record('resource', resource['id'])
        cached_calculation = False
        if data_quality:
            self.logger.debug('Data Quality calculated for '
                              'version modified on: %s',
                              data_quality.resource_last_modified)
            if data_quality.resource_last_modified >= last_modified:
                cached_calculation = True
                # check if all metrics have been calculated or some needs to be
                # calculated again
                if all(map(lambda m: m is not None,
                           [
                            data_quality.completeness,
                            data_quality.uniqueness,
                            data_quality.accuracy,
                            data_quality.validity,
                            data_quality.timeliness,
                            data_quality.consistency
                          ])):
                    self.logger.debug('Data Quality already calculated.')
                    return data_quality.metrics
                else:
                    self.logger.debug('Data Quality not calculated for all dimensions.')
            else:
                self.logger.debug('Resource changes since last calculated. '
                            'Calculating data quality again.')
        else:
            data_quality = DataQualityMetricsModel(type='resource',
                                                   ref_id=resource['id'])
            data_quality.resource_last_modified = last_modified
            self.logger.debug('First data quality calculation.')
        data_quality.ref_id = resource['id']

        data_quality.resource_last_modified = last_modified
        results = {}
        for metric in self.metrics:
            try:
                if cached_calculation and getattr(data_quality, metric.name) is not None:
                    cached = data_quality.metrics[metric.name]
                    if not cached.get('failed'):
                        self.logger.debug('Dimension %s already calculated. Skipping...', metric.name)
                        results[metric.name] = cached
                        continue
                self.logger.debug('Calculating dimension: %s...', metric)
                results[metric.name] = metric.calculate_metric(resource, data)
            except Exception as e:
                self.logger.error('Failed to calculate metric: %s. Error: %s',
                                  metric, str(e))
                self.logger.exception(e)
                results[metric.name] = {
                    'failed': True,
                    'error': str(e),
                }

        # set results
        for metric, result in results.items():
            if result.get('value') is not None:
                setattr(data_quality, metric, result['value'])

        data_quality.metrics = results
        data_quality.modified_at = datetime.now()
        data_quality.save()
        self.logger.debug('Metrics calculated for resource: %s',
                          resource['id'])
        return results

    def calculate_cumulative_metrics(self, package_id, resources, results):
        self.logger.debug('Cumulative data quality metrics for package: %s',
                          package_id)
        data_quality = self._get_metrics_record('package', package_id)
        if not data_quality:
            data_quality = DataQualityMetricsModel(type='package')
            data_quality.ref_id = package_id
        cumulative = {}
        for metric in self.metrics:
            metric_results = [res.get(metric.name, {}) for res in results]
            cumulative[metric.name] = metric.calculate_cumulative_metric(
                resources,
                metric_results
            )

        for metric, result in cumulative.items():
            if result.get('value') is not None:
                setattr(data_quality, metric, result['value'])

        data_quality.metrics = cumulative
        data_quality.modified_at = datetime.now()
        data_quality.save()
        self.logger.debug('Cumulative metrics calculated for: %s', package_id)


class Completeness(DimensionMetric):

    def __init__(self):
        super(Completeness, self).__init__('completeness')

    def calculate_metric(self, resource, data):
        columns_count = len(data['fields'])
        rows_count = data['total']
        total_values_count = columns_count * rows_count

        self.logger.debug('Rows: %d, Columns: %d, Total Values: %d',
                          rows_count, columns_count, total_values_count)

        total_complete_values = 0
        for row in data['records']:
            total_complete_values += self._completenes_row(row)

        result = float(total_complete_values)/float(total_values_count) * 100.0
        self.logger.debug('Complete (non-empty) values: %s',
                          total_complete_values)
        self.logger.debug('Completeness score: %f%%', result)
        return {
            'value': result,
            'total': total_values_count,
            'complete': total_complete_values,
        }

    def _completenes_row(self, row):
        count = 0
        for _, value in row.items():
            if value is None:
                continue
            if isinstance(value, str):
                if not value.strip():
                    continue
            count += 1
        return count

    def calculate_cumulative_metric(self, resources, metrics):
        total, complete = reduce(lambda (total, complete), result: (
            total + result['total'],
            complete + result['complete']), metrics, (0, 0))
        return {
            'total': total,
            'complete': complete,
            'value': float(complete)/float(total) * 100.0,
        }


class Uniqueness(DimensionMetric):

    def __init__(self):
        super(Uniqueness, self).__init__('uniqueness')
    
    def calculate_metric(self, resource, data):
        total = {}
        distinct = {}

        for row in data['records']:
            for col, value in row.items():
                total[col] = total.get(col, 0) + 1
                if distinct.get(col) is None:
                    distinct[col] = set()
                distinct[col].add(value)
        
        result = {
            'total': sum(v for _,v in total.items()),
            'unique': sum([len(s) for _,s in distinct.items()]), 
            'columns': {},
        }
        result['value'] = 100.0*float(result['unique'])/float(result['total']) if result['total'] > 0 else 0.0

        for col, tot in total.items():
            unique = len(distinct.get(col, set()))
            result['columns'][col] = {
                'total': tot,
                'unique': unique,
                'value': 100.0*float(unique)/float(tot) if tot > 0 else 0.0,
            }
        return result

    def calculate_cumulative_metric(self, resources, metrics):
        result = {}
        result['total'] = sum([r['total'] for r in metrics])
        result['unique'] = sum([r['unique'] for r in metrics])

        result['value'] = 100.0*float(result['unique'])/float(result['total']) if result['total'] > 0 else 0.0

        return result


class Timeliness(DimensionMetric):

    def __init__(self):
        super(Timeliness, self).__init__('timeliness')

    def calculate_metric(self, resource, data):
        settings = resource.get('data_quality_settings', {}).get('timeliness', {})
        print 'DQ Settings ->', resource.get('data_quality_settings', {})
        column = settings.get('column')
        if not column:
            self.logger.warning('No column for record entry date defined '
                                'for resource %s', resource['id'])
            return {
                'failed': True,
                'error': 'No date column defined in settings',
            }
        dt_format = settings.get('date_format')
        parse_date_column = lambda ds: dateutil.parser.parse(ds)
        if dt_format:
            parse_date_column = lambda ds: datetime.strptime(ds, dt_format)
        
        created = dateutil.parser.parse(resource['created'])

        measured_count = 0
        total_delta = 0

        for row in data['records']:
            value = row.get(column)
            if value:
                try:
                    record_date = parse_date_column(value)
                    if record_date > created:
                        self.logger.warning('Date of record creating is after the time it has entered the system.')
                        continue
                    delta = created - record_date
                    total_delta += delta.total_seconds()
                    measured_count += 1
                except Exception as e:
                    self.logger.debug('Failed to process value: %s. Error: %s', value, str(e))
        if measured_count == 0:
            return {
                'value': '',
                'total': 0,
                'average': 0,
                'records': 0,
            }
        avg_delay = timedelta(seconds=int(total_delta/measured_count))

        self.logger.debug('Measured records: %d of %d.', measured_count, data.get('total', 0))
        self.logger.debug('Total delay: %s (%d seconds).', str(total_delta), total_delta)
        self.logger.debug('Average delay: %s (%d seconds).', str(avg_delay), avg_delay.total_seconds())

        return {
            'value': '+%s' % str(avg_delay),
            'total': int(total_delta),
            'average': avg_delay.total_seconds(),
            'records': measured_count,
        }

    def calculate_cumulative_metric(self, resources, metrics):
        total_delay = sum([r.get('total', 0) for r in metrics])
        total_records = sum([r.get('records', 0) for r in metrics])
        if not total_records:
            return {
                'value': '',
                'total': int(total_delay),
                'average': 0,
                'records': 0,
            }
        avg_delay = int(total_delay/total_records)
        return {
            'value': '+%s' % str(timedelta(seconds=avg_delay)),
            'total': int(total_delay),
            'average': avg_delay,
            'records': total_records,
        }

class Validity(DimensionMetric):

    def __init__(self):
        super(Validity, self).__init__('validity')


class Accuracy(DimensionMetric):

    def __init__(self):
        super(Accuracy, self).__init__('accuracy')
    
    def calculate_metric(self, resource, data):
        settings = resource.get('data_quality_settings', {}).get('accuracy', {})
        column = settings.get('column')
        if not column:
            self.logger.error('Cannot calculate accuracy on this resource '
                              'because no accuracy column is specified.')
            return {
                'failed': True,
                'error': 'Missing accuracy column.',
            }
        
        accurate = 0
        inaccurate = 0

        for row in data['records']:
            flag = row.get(column)
            if flag is None or flag.strip() == '':
                # neither accurate or inaccurate
                continue
            if flag.lower() in ['1', 'yes', 'accurate', 't', 'true']:
                accurate += 1
            else:
                inaccurate += 1
        
        total = accurate + inaccurate
        value = 0.0
        if total:
            value = float(accurate)/float(total) * 100.0
        
        self.logger.debug('Accurate: %d', accurate)
        self.logger.debug('Inaccurate: %d', inaccurate)
        self.logger.debug('Accuracy: %f%%', value)
        return {
            'value': value,
            'total': total,
            'accurate': accurate,
            'inaccurate': inaccurate,
        }

    def calculate_cumulative_metric(self, resources, metrics):
        accurate = sum([r.get('accurate', 0) for r in metrics])
        inaccurate = sum([r.get('inaccurate', 0) for r in metrics])

        total = accurate + inaccurate
        value = 0.0
        if total:
            value = float(accurate)/float(total) * 100.0
        
        return {
            'value': value,
            'total': total,
            'accurate': accurate,
            'inaccurate': inaccurate,
        }


class Consistency(DimensionMetric):

    def __init__(self):
        super(Consistency, self).__init__('consistency')
