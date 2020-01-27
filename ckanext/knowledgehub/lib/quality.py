import ckan.plugins.toolkit as toolkit
import ckan.lib.uploader as uploader
from ckanext.knowledgehub.model.data_quality import (
    DataQualityMetrics as DataQualityMetricsModel
)
from logging import getLogger
from functools import reduce
from datetime import datetime, timedelta
import dateutil
import json
import re

import requests
from goodtables import validate


log = getLogger(__name__)


class LazyStreamingList(object):

    def __init__(self, fetch_page, page_size=512):
        self.fetch_page = fetch_page
        self.page_size = page_size
        self.page = 0
        self.buffer = None
        self.total = 0
    
    def _fetch_buffer(self):
        if self.total:
            if self.page*self.page_size >= self.total:
                self.buffer = []
                return
        result = self.fetch_page(self.page, self.page_size)
        self.total = result.get('total', 0)
        self.buffer = result.get('records', [])
        self.page += 1

    def iterator(self):
        current = 0
        self._fetch_buffer()
        while True:
            if current >= self.total or not self.buffer:
                # end of all results
                raise StopIteration()
            for row in self.buffer:
                current += 1
                yield row
            # fetch next buffer
            self._fetch_buffer()
    
    def __iter__(self):
        return self.iterator()


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

        def _fetch_page(page, page_size):
            try:
                context = {'ignore_auth': True}
                return toolkit.get_action('datastore_search')(context, {
                    'resource_id': resource['id'],
                    'offset': page*page_size,
                    'limit': page_size,
                })
            except Exception as e:
                self.logger.warning('Failed to fetch data for resource %s. Error: %s', resource['id'], str(e))
                self.logger.exception(e)
                return {
                    'total': 0,
                    'records': [],
                }

        result = _fetch_page(0, 1)  # to calculate the total from start
        return {
            'total': result.get('total', 0),
            'records': LazyStreamingList(_fetch_page),
            'fields': result['fields'], # metadata
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
            result = self.calculate_metrics_for_resource(resource)
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

    def calculate_metrics_for_resource(self, resource):
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
                self.logger.debug('Resource changed since last calculated. '
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
                    if cached.get('manual'):
                        self.logger.debug('Calculation has been performed manually. Skipping...', metric.name)
                        results[metric.name] = cached
                        continue
                    
                self.logger.debug('Calculating dimension: %s...', metric)
                data_stream = self._fetch_resource_data(resource) # data is a stream
                results[metric.name] = metric.calculate_metric(resource, data_stream)
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
        dataset_results = data_quality.metrics or {}
        for metric in self.metrics:
            cached = dataset_results.get(metric.name, {})
            if cached.get('manual'):
                self.logger.debug('Metric %s is calculated manually. Skipping...', metric.name)
                cumulative[metric.name] = cached
                continue
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
            total + result.get('total', 0),
            complete + result.get('complete', 0)
        ), metrics, (0, 0))
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

    def _perform_validation(self, resource, total_rows):
        rc = {}
        rc.update(resource)
        rc['validation_options'] = {
            'row_limit': total_rows,
        }
        return validate_resource_data(rc)

    def calculate_metric(self, resource, data):
        validation = None
        try:
            validation = self._perform_validation(resource, data.get('total', 0))
        except Exception as e:
            self.logger.error('Failed to validate data for resource: %s. Error: %s', resource['id'], str(e))
            self.logger.exception(e)
            return {
                'failed': True,
                'error': str(e),
            }

        total_rows = 0
        total_errors = 0
        for table in validation.get('tables', []):
            total_rows += table.get('row-count', 0)
            total_errors += table.get('error-count', 0)
        
        if total_rows == 0:
            return {
                'value': 0.0,
                'total': 0,
                'valid': 0,
            }
        
        valid = total_rows - total_errors
        value = float(valid)/float(total_rows) * 100.0

        return {
            'value': value,
            'total': total_rows,
            'valid': valid,
        }

    def calculate_cumulative_metric(self, resources, metrics):
        total = sum([r.get('total', 0) for r in metrics])
        valid = sum([r.get('valid', 0) for r in metrics])
        if total == 0:
            return {
                'value': 0.0,
                'total': 0,
                'valid': 0,
            }
        
        return {
            'value': float(total)/float(valid) * 100.0,
            'total': total,
            'valid': valid,
        }

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
    
    def validate_date(self, field, value, _type, report):
        date_format = detect_date_format(value) or 'unknown'
        report['formats'][date_format] = report['formats'].get(date_format, 0) + 1

    def validate_numeric(self, field, value, _type, report):
        num_format = detect_numeric_format(value) or 'unknown'
        report['formats'][num_format] = report['formats'].get(num_format, 0) + 1

    def validate_int(self, field, value, _type, report):
        num_format = detect_numeric_format(value) or 'unknown'
        report['formats'][num_format] = report['formats'].get(num_format, 0) + 1

    def validate_string(self, field, value, _type, report):
        report['formats'][_type] = report['formats'].get(_type, 0) + 1

    def get_consistency_validators(self):
        return {
            'timestamp': self.validate_date,
            'numeric': self.validate_numeric,
            'int': self.validate_int,
            'string': self.validate_string,
            'text': self.validate_string,
        }

    def calculate_metric(self, resource, data):
        validators = self.get_consistency_validators()
        fields = {f['id']: f for f in data['fields']}
        report = {f['id']: {'count': 0, 'formats': {}} for f in data['fields']}

        for row in data['records']:
            for field, value in row.items():
                field_type = fields.get(field, {}).get('type')
                validator = validators.get(field_type)
                field_report = report[field]
                if validator:
                    validator(field, value, field_type, field_report)
                    field_report['count'] += 1
        
        for field, field_report in report.items():
            most_consistent = max([count for _,count in field_report['formats'].items()])
            field_report['consistent'] = most_consistent

        total = sum([f.get('count', 0) for _, f in report.items()])
        consistent = sum([f.get('consistent', 0) for _, f in report.items()])
        value = float(consistent)/float(total) * 100.0
        return {
            'total': total,
            'consistent': consistent,
            'value': value,
            'report': report,
        }
    
    def calculate_cumulative_metric(self, resources, metrics):
        total = sum([r.get('total', 0) for r in metrics])
        consistent = sum([r.get('consistent', 0) for r in metrics])
        value = float(consistent)/float(total) * 100.0
        return {
            'total': total,
            'consistent': consistent,
            'value': value,
        }


# Date format utils

_all_date_formats = [
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%dT%H:%M:%SZ',
    '%Y-%m-%dT%H:%M:%S.%fZ',
    '%Y-%m-%dT%H:%M:%S%Z',
    '%Y-%m-%dT%H:%M:%S.%f%Z',
]

_all_numeric_formats = [
    r'$\d+^',
    r'$[+-]\d+^',
    r'$(\d{1,3},)+^',
    r'$(\d{1,3},)+\.\d+^',
    r'$[+-](\d{1,3},)+^',
    r'$[+-](\d{1,3},)+\.\d+^',
    r'$\d+\.\d+^',
    r'$[+-]\d+\.\d+^',
]

def detect_date_format(datestr):
    if re.match(r'$\d^', datestr):
        return 'unix-timestamp'
    if re.match(r'$\d+\.\d+', datestr):
        return 'timestamp'
    if re.match(r'$\d+[\+\-]\d+^', datestr):
        return 'timestamp-tz'
    for dt_format in _all_date_formats:
        try:
            datetime.strptime(datestr, dt_format)
            return dt_format
        except:
            pass
    return None

def detect_numeric_format(numstr):
    for parser in [int, float]:
        try:
            parser(numstr)
            return parser.__name__
        except:
            pass
    
    for num_format in _all_numeric_formats:
        m = re.match(num_format, numstr)
        if m:
            return num_format
        return None

# resource validation
def validate_resource_data(resource):
    log.debug(u'Validating resource {}'.format(resource['id']))

    options = toolkit.config.get(
        u'ckanext.validation.default_validation_options')
    if options:
        options = json.loads(options)
    else:
        options = {}

    resource_options = resource.get(u'validation_options')
    if resource_options and isinstance(resource_options, basestring):
        resource_options = json.loads(resource_options)
    if resource_options:
        options.update(resource_options)

    dataset = toolkit.get_action('package_show')(
        {'ignore_auth': True}, {'id': resource['package_id']})

    source = None
    if resource.get(u'url_type') == u'upload':
        upload = uploader.get_resource_uploader(resource)
        if isinstance(upload, uploader.ResourceUpload):
            source = upload.get_path(resource[u'id'])
        else:
            # Upload is not the default implementation (ie it's a cloud storage
            # implementation)
            pass_auth_header = toolkit.asbool(
                toolkit.config.get(u'ckanext.validation.pass_auth_header', True))
            if dataset[u'private'] and pass_auth_header:
                s = requests.Session()
                s.headers.update({
                    u'Authorization': t.config.get(
                        u'ckanext.validation.pass_auth_header_value',
                        _get_site_user_api_key())
                })

                options[u'http_session'] = s

    if not source:
        source = resource[u'url']

    schema = resource.get(u'schema')
    if schema and isinstance(schema, basestring):
        if schema.startswith('http'):
            r = requests.get(schema)
            schema = r.json()
        else:
            schema = json.loads(schema)

    _format = resource[u'format'].lower()

    report = _validate_table(source, _format=_format, schema=schema, **options)

    # Hide uploaded files
    for table in report.get('tables', []):
        if table['source'].startswith('/'):
            table['source'] = resource['url']
    for index, warning in enumerate(report.get('warnings', [])):
        report['warnings'][index] = re.sub(r'Table ".*"', 'Table', warning)

    return report


def _validate_table(source, _format=u'csv', schema=None, **options):
    report = validate(source, format=_format, schema=schema, **options)

    log.debug(u'Validating source: {}'.format(source))

    return report


def _get_site_user_api_key():
    site_user_name = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    site_user = toolkit.get_action('get_site_user')(
        {'ignore_auth': True}, {'id': site_user_name})
    return site_user['apikey']