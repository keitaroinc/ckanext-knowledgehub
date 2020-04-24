# -*- coding: UTF-8 -*-

import ckan.plugins.toolkit as toolkit
import ckan.lib.uploader as uploader
import ckan.lib.helpers as helpers
from ckan.model import Session, User, user_table
from ckanext.knowledgehub.model.data_quality import (
    DataQualityMetrics as DataQualityMetricsModel
)
from logging import getLogger
from functools import reduce
from datetime import datetime, timedelta
import dateutil
import json
import re
import csv
from tempfile import TemporaryFile
import paste.fileapp
import os.path

import requests
from goodtables import validate


log = getLogger(__name__)


class LazyStreamingList(object):
    '''Implements a buffered stream that emulates an iterable object.

    It is used to fetch large data in chunks (pages/buffers). The fetch is
    done using a buffer of predefined size. While the iterator iterates over
    the buffer, when the end of the buffer is reached, a call is made to fetch
    the next buffer before iterating to the next record.

    :param fetch_page: `function`, a function used to fetch the next buffer
        data. The function prototype is:

            .. code-block: python

                def fetch_page(page, page_size):
                    return {
                        'total': 100,
                        'records': [...],
                    }

        The function takes two parameters:
            * `page`, `int`, the page number starting from 0
            * `page_size`, `int`, the number of items per page. Default is 512.

        The function must return a dict containing the records. The dict must
        have the following entries:
            * `total` - total number of items
            * `records` - a list (iterable) over the records fetched for this
                page.
    :param page_size: `int`, the size of each page (buffer). Default is 512.
    '''

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
        '''Returns an iterator over all of the records.
        '''
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

    def rewind(self):
        self.buffer = None
        self.page = 0
        self.total = 0


class ResourceCSVData(object):
    '''Represents a CSV data source that can be read with pagination.

    It fetches the CSV data (for a resource) and generates metadata related to
    the CSV file data.
    The column names and data types for each column are calculated:
        * column names are calculated from the firs row in the CSV file. If
            there are multiple columns with the same name, then the column
            names are suffixed with index `_<i>`, for example:
                - if we have the following columns: `a`, `b`, `a`, `a`, then
                the generated columns will have the following names: `a_1`,
                `b`, `a_2` and `a_3`.
        * the data types are guessed from the first row with data (second row
        in the file).

    The data is rerieved in pages. Each page is a `dict` containing:
        * `total` - total number of data rows in the CSV file (the header row
            is not counted)
        * `records` - the records in the requested page - a `list` of `dict`
        * `fields` - `list` of `dict` describing the columns in the CSV file.

    The constructor takes one argument - the data loader for the CSV. This is a
    function (callable) that is called without arguments to load the actual
    data from the CSV file. The expected output of this function is a `list`
    of rows where each row is itself a `list` of values.
    '''

    def __init__(self, resource_loader):
        csv_data = resource_loader()
        self.data = csv_data
        self.fields = self._get_field_types(self._get_fields(csv_data),
                                            csv_data)
        self.column_names = [f['id'] for f in self.fields]
        self.total = 0
        if len(csv_data):
            self.total = len(csv_data) - 1
        log.debug('%s, Resource CSV data. Total: %d, columns=%s, fields=%s',
                  str(self), self.total, self.column_names, self.fields)

    def _get_fields(self, csv_data):
        if not csv_data:
            return {}
        columns = csv_data[0]
        columns_count = {}
        for column in columns:
            columns_count[column] = columns_count.get(column, 0) + 1
        numbered = {}
        fields = []
        for column in columns:
            if columns_count[column] > 1:
                numbered[column] = numbered.get(column, 0) + 1
                column = '{}_{}'.format(column, numbered[column])
            fields.append({'id': column})
        return fields

    def _get_field_types(self, fields, csv_data):
        if not csv_data or len(csv_data) == 1:
            for field in fields:
                field['type'] = 'text'
            return fields
        row = csv_data[1]
        for i, field in enumerate(fields):
            field['type'] = self._guess_type(row[i])
        return fields

    def _guess_type(self, value):
        if value is None:
            return 'text'
        if detect_numeric_format(value):
            return 'numeric'
        if detect_date_format(value):
            return 'timestamp'
        return 'text'

    def fetch_page(self, page, limit):
        '''Retrieves one page from the CSV data.

        :param page: `int`, the number of the page to fetch, 0-based.
        :param limit: `int`, the page size.

        :returns: the data page, which is a `dict` containing:
            * `total` - total number of records.
            * `records` - `list` of `dict`, the row (records) in this page.
            * `fields` - `list` of `dict`, metadata for the columns.
        '''
        start = max(page, 0) * limit + 1
        limit = min(start + limit, self.total + 1)
        items = []
        if start < (self.total + 1):
            for i in range(start, limit):
                data_row = self.data[i]
                row_dict = {self.column_names[j]: value
                            for j, value in enumerate(data_row)}
                items.append(row_dict)
        log.debug('ResourceCSVData.fetch_page: '
                  'page=%d, limit=%d, of total %d. Got %d results.',
                  page, limit, self.total, len(items))
        return {
            'total': self.total,
            'records': items,
            'fields': self.fields,
        }


class ResourceFetchData(object):
    '''A callable wrapper for fetching the resource data.

    Based on the availability of the data, when called it will fetch a page of
    the resource data.
    The data for a particular resource may be stored in the Data Store, in CKAN
    storage path or on a remote server. Ideally we want to read the data from
    the data store, however if the data is not available there, we should try
    to download the CSV data directly - either from CKAN or if the resource was
    set as a link to an external server, by downloading it from that server.

    :param resource: `dict`, the resource metadata as retrieved from CKAN
        action `resource_show`.
    '''

    def __init__(self, resource):
        self.resource = resource
        self.download_resource = False
        self.resource_csv = None

    def __call__(self, page, limit):
        '''Fetches one page (with size of `limit`) of data from the resource
        CSV data.

        This call will first try to load the data from the datastore. If that
        fails and the data is not available in the data store, then it will try
        to load the data directly (from CKAN uploads or by downloading the CSV
        file directly from the remote server). Once this happens, and the data
        is loaded into `ResourceCSVData`, then every subsequent call will load
        the data from the cached instance of `ResourceCSVData` and will not try
        to load it from the data store.

        :param page: `int`, the page to fetch, 0-based.
        :param limit: `int`, page size.

        :returns: `dict`, the requested page as `dict` containing:
            * `total` - total number of records in the data.
            * `records` - a `list` of records for this page. Each record is a
                `dict` of format `<column_name>:<row_value>`.
            * `fields` - the records metadata describing each column. It is a
                `list` of `dict`, where each element describes one column. The
                order of the columns is the same as it is appears in the CSV
                file. Each element has:
                    * `id` - `str`, the name of the column
                    * `type` - `str`, the column type (ex. `numeric`, `text`)
        '''
        try:
            page = self.fetch_page(page, limit)
            return page
        except Exception as e:
            log.error('Failed to fetch page %d (limit %d) of resource %s. '
                      'Error: %s',
                      page,
                      limit,
                      self.resource.get('id'),
                      str(e))
            log.exception(e)
            return {
                'total': 0,
                'records': [],
                'fields': {},
            }

    def _fetch_data_datastore(self, page, limit):
        log.debug('Fetch page from datastore: page %d, limit %d', page, limit)
        return toolkit.get_action('datastore_search')({
            'ignore_auth': True,
        }, {
            'resource_id': self.resource['id'],
            'offset': page*limit,
            'limit': limit,
        })

    def _download_resource_from_url(self, url, headers=None):
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()  # Raise an error if request to file failed.
        data = []
        with TemporaryFile(mode='w+b') as tmpf:
            for chunk in resp.iter_content():
                tmpf.write(chunk)
            tmpf.flush()
            tmpf.seek(0, 0)  # rewind to start
            reader = csv.reader(tmpf)
            for row in reader:
                data.append(row)
        return data

    def _download_resource_from_ckan(self, resource):
        upload = uploader.get_resource_uploader(resource)
        filepath = upload.get_path(resource['id'])
        try:
            data = []
            if os.path.isfile(filepath):
                data = []
                with open(filepath) as csvf:
                    reader = csv.reader(csvf)
                    for row in reader:
                        data.append(row)
                return data
            else:
                # The worker is not in the same machine as CKAN, so it cannot
                # read the resource files from the local file system.
                # We need to retrieve the resource data from the resource URL.
                if 'url' not in resource:
                    raise Exception('Cannot access the resource because the '
                                    'resource URL is not set.')
                log.debug('Resource data is not in this file system '
                          '(File %s does not exist).'
                          'Fetching data from CKAN download url directly.',
                          filepath)
                headers = None
                sysadmin_api_key = _get_sysadmin_user_key()
                if sysadmin_api_key:
                    headers = {'Authorization': sysadmin_api_key}
                return self._download_resource_from_url(
                    resource['url'],
                    headers
                )
        except OSError as e:
            log.error('Failed to download resource from CKAN upload. '
                      'Error: %s', str(e))
            log.exception(e)
            raise e

    def _fetch_data_directly(self):
        if self.resource.get('url_type') == 'upload':
            log.debug('Getting data from CKAN...')
            return self._download_resource_from_ckan(self.resource)
        if self.resource.get('url'):
            log.debug('Getting data from remote URL...')
            return self._download_resource_from_url(self.resource['url'])
        raise Exception('Resource {} is not available '
                        'for download.'.format(self.resource.get('id')))

    def fetch_page(self, page, limit):
        '''Fetches one page (with size of `limit`) of data from the resource
        CSV data.

        This call will first try to load the data from the datastore. If that
        fails and the data is not available in the data store, then it will try
        to load the data directly (from CKAN uploads or by downloading the CSV
        file directly from the remote server). Once this happens, and the data
        is loaded into `ResourceCSVData`, then every subsequent call will load
        the data from the cached instance of `ResourceCSVData` and will not try
        to load it from the data store.

        :param page: `int`, the page to fetch, 0-based.
        :param limit: `int`, page size.

        :returns: `dict`, the requested page as `dict` containing:
            * `total` - total number of records in the data.
            * `records` - a `list` of records for this page. Each record is a
                `dict` of format `<column_name>:<row_value>`.
            * `fields` - the records metadata describing each column. It is a
                `list` of `dict`, where each element describes one column. The
                order of the columns is the same as it is appears in the CSV
                file. Each element has:
                    * `id` - `str`, the name of the column
                    * `type` - `str`, the column type (ex. `numeric`, `text`)
        '''
        if self.download_resource:
            if not self.resource_csv:
                self.resource_csv = ResourceCSVData(self._fetch_data_directly)
                log.debug('Resource data downloaded directly.')
            return self.resource_csv.fetch_page(page, limit)
        try:
            page = self._fetch_data_datastore(page, limit)
            log.debug('Data is available in DataStore. '
                      'Using datastore for data retrieval.')
            return page
        except Exception as e:
            log.warning('Failed to load resource data from DataStore. '
                        'Error: %s', str(e))
            log.exception(e)
            self.download_resource = True
            log.debug('Will try to download the data directly.')
            return self.fetch_page(page, limit)


def _get_sysadmin_user():
    '''Find a sysadmin user in the CKAN database.
    '''
    q = Session.query(User)
    q = q.filter(user_table.c.state == 'active')
    q = q.filter(user_table.c.sysadmin == True)

    return q.first()


def _get_sysadmin_user_key():
    '''Returns the API key of a sysadmin user of CKAN (if any).
    The API key may be of any of the sysadmin users of the portal, there is no
    guarantee to which user this key belongs to.

    If no admin users exist (or are not active), then `None` is returned.
    '''
    sysadmin = _get_sysadmin_user()
    if sysadmin:
        return sysadmin.apikey
    return None


class DimensionMetric(object):
    '''Makes a measurement for one of the Data Quality dimensions.

    Defines two methods for mesurement: one to measure the dimension for one
    resource over the resource data; and then to calculate cumulative metrics
    for multiple resources given the results of the previous calculation for
    each resource.

    In practice this would amount to something like this:

        .. code-block: python

            metrics = []
            for resource in resources:
                # calculate the dimension metric for this resource
                data = fetch_resource_data(resource)
                result = dimension_metric.calculate_metric(resource, data)
                metrics.append(result)

            # now we can calculate the cumulative metrics for all resources
            report = dimension_metric.calculate_cumulative_metric(resources,
                                                                  metrics)

    :param name: `str`, the name of the dimension.
    '''
    def __init__(self, name):
        self.name = name
        self.logger = getLogger('ckanext.data_quality.%s' % self.name)

    def calculate_metric(self, resource, data):
        '''Calculates the dimension of the data quality for the given resource
        over the resource data.

        :param resource: `dict`, the resource as fetched from CKAN
        :param data: `dict`, the resource data. The dict will contain the
            following entries:
                * `total`, `int`, total number of records.
                * `fields`, `list` of `dict`, metadata for the fields in the
                    tabular data.
                * `records`, `iterable`, an iterable object over all of the
                    records for the data of this resource.

        :returns: `dict`, a report on the dimension metric. The dict can
            contain the following entries:
            * `value`, populated if the calculation was successful, and it will
                contain the calculated value for the dimension.
            * `failed`, `boolean`, optional, if set, then it means that the
                calculation has failed for some reason. If not present in the
                report dict, then the calculation was successful.
            * `error`, `str`, optional, set only if `failed` is set to `True`.
                Contains the reason/error for the calculation failure.
        '''
        return {}

    def calculate_cumulative_metric(self, resources, metrics):
        '''Reduces the calculations of multiple resources into one report.

        :param resources: `list` of CKAN resources. The resources for which
            a calculation has been performed
        :param metrics: `list` of dimension metric calculations for the given
            resources. See `DimensionMetric.calculate_metric` for the format of
            the result `dict` for the metric calculation. The number of results
            and resources must be the same and the order in resources must
            correspond with the order of the results in `metrics`.

        :returns: `dict`, a cumulative (reduce) report for the metrics of all
            resources. The report `dict` can contain the following entries:
            * `value`, populated if the calculation was successful, and it will
                contain the calculated value for the dimension.
            * `failed`, `boolean`, optional, if set, then it means that the
                calculation has failed for some reason. If not present in the
                report dict, then the calculation was successful.
            * `error`, `str`, optional, set only if `failed` is set to `True`.
                Contains the reason/error for the calculation failure.
        '''
        return {}

    def __str__(self):
        return 'DataQualityDimension<%s>' % self.name


class DataQualityMetrics(object):
    '''Calculates Data Quality metrics for multiple dimensions for all
    resouces in a dataset.

    The calculation is performed in two phases:
        1. Data Quality metrics are calculated for all dimensions for each of
        the dataset resources (map phase). The results of each calculation are
        kept and used in the seconds phase (reduce phase).
        2. All of the results for all resources are then processed and reduced
        to calculate the metrics for all dimensions for the dataset.
    Results of the calculations for all entities (resources and the dataset)
    are stored in database.

    :param metrics: `list` of `DimensionMetric`, the dimensions for which to
        calculate Data Quality on a given dataset.
    :param force_recalculate: `boolean`, force recalculation of the data
        quality metrics even if the data has not been modified.
    '''
    def __init__(self, metrics=None, force_recalculate=False):
        self.metrics = metrics or []
        self.force_recalculate = force_recalculate
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
                return toolkit.get_action('datastore_search')(None, {
                    'resource_id': resource['id'],
                    'offset': page*page_size,
                    'limit': page_size,
                })
            except Exception as e:
                self.logger.warning('Failed to fetch data for resource %s. '
                                    'Error: %s', resource['id'], str(e))
                self.logger.exception(e)
                return {
                    'total': 0,
                    'records': [],
                }

        _fetch_page = ResourceFetchData(resource)

        result = _fetch_page(0, 1)  # to calculate the total from start
        return {
            'total': result.get('total', 0),
            'records': LazyStreamingList(_fetch_page),
            'fields': result['fields'],  # metadata
        }

    def _get_metrics_record(self, ref_type, ref_id):
        metrics = DataQualityMetricsModel.get(ref_type, ref_id)
        return metrics

    def _new_metrics_record(self, ref_type, ref_id):
        return DataQualityMetricsModel(type=ref_type, ref_id=ref_id)

    def calculate_metrics_for_dataset(self, package_id):
        '''Calculates the Data Qualtity for the given dataset identified with
        `package_id`.

        The metrics for the resources and dataset are calculated or reused from
        an earlier calculation if there were no changes in the resources data
        from the last time the calculation has been performed.

        Additionaly, if some of the metrics were set manually, either for a
        resource or the dataset, then the calculation for that dimension will
        not be performed and the manual value will be kept intact.

        The calculations for both resources and dataset are kept in a database,
        one entry for dataset and one for each resource.

        :param package_id: `str`, the ID of the dataset (package) for which to
            calculate Data Quality metrics.
        '''
        self.logger.debug('Calculating data quality for dataset: %s',
                          package_id)
        dataset = self._fetch_dataset(package_id)
        results = []
        for resource in dataset['resources']:
            self.logger.debug('Calculating data quality for resource: %s',
                              resource['id'])
            resource['data_quality_settings'] = self._data_quality_settings(
                resource)
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
        '''Performs a calculation for Data Quality for a particular resource.

        Data Quality is calculated for each dimension separately and a report
        is returned containing the values for all dimensions.

        The calculation will reuse the results from a previous run if the
        resource data has not changed since the last time the calculation was
        performed. This rule is applied for each dimension separately, so a
        result can be cached for some of the dimensions, and will be calculated
        a new for those dimensions that have not been calculted in the previous
        run.

        If a metric for specific dimension has been set manually, then no
        calculation is performed for that dimension and the manual values are
        kept.

        :param resource: `dict`, CKAN resource metadata.

        :returns: `dict`, a report for all calculated metrics for this resource
            data. The report `dict` has the following structure:

                .. code-block: python
                    report = {
                        '<dimension>': {
                            'value': 90.0, # the calculated value
                            '<other_data>': ...
                        }
                    }

            The result dict for each dimension will always contain an entry
            with the calculated value (called `value`), but also may contain
            any additional entries from the calculation itself, such as:
                * `total` - total number of processed entries
                * `failed` - if present it means that the calculation for that
                    dimension has failed.
                * `error` - the actual error that happened, if `failed` is set.

        '''
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
                if all(map(lambda m: m is not None, [
                            data_quality.completeness,
                            data_quality.uniqueness,
                            data_quality.accuracy,
                            data_quality.validity,
                            data_quality.timeliness,
                            data_quality.consistency])):
                    self.logger.debug('Data Quality already calculated.')
                    return data_quality.metrics
                else:
                    self.logger.debug('Data Quality not calculated for '
                                      'all dimensions.')
            else:
                data_quality = self._new_metrics_record('resource',
                                                        resource['id'])
                data_quality.resource_last_modified = last_modified
                self.logger.debug('Resource changed since last calculated. '
                                  'Calculating data quality again.')
        else:
            data_quality = self._new_metrics_record('resource', resource['id'])
            data_quality.resource_last_modified = last_modified
            self.logger.debug('First data quality calculation.')

        data_quality.ref_id = resource['id']

        data_quality.resource_last_modified = last_modified
        results = {}
        data_stream = None
        if self.force_recalculate:
            log.info('Forcing recalculation of the data metrics '
                     'has been set. All except the manually set metric data '
                     'will be recalculated.')
        for metric in self.metrics:
            try:
                if cached_calculation and getattr(data_quality,
                                                  metric.name) is not None:
                    cached = data_quality.metrics[metric.name]
                    if not self.force_recalculate and not cached.get('failed'):
                        self.logger.debug('Dimension %s already calculated. '
                                          'Skipping...', metric.name)
                        results[metric.name] = cached
                        continue
                    if cached.get('manual'):
                        self.logger.debug('Calculation has been performed '
                                          'manually. Skipping...', metric.name)
                        results[metric.name] = cached
                        continue

                self.logger.debug('Calculating dimension: %s...', metric)
                if not data_stream:
                    data_stream = self._fetch_resource_data(resource)
                else:
                    if data_stream.get('records') and \
                            hasattr(data_stream['records'], 'rewind'):
                        data_stream['records'].rewind()
                    else:
                        data_stream = self._fetch_resource_data(resource)
                results[metric.name] = metric.calculate_metric(resource,
                                                               data_stream)
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
        '''Calculates the cumulative metrics (reduce phase), from the results
        calculated for each resource in the dataset.

        The cumulative values for the dataset are always calculated from the
        results, except in the case when the values for a particular dimension
        have been set manually. In that case, the manual value is used.

        The results of the calculation are stored in database in a separate
        entry containing the valued for Data Quality metrics for the whole
        dataset.

        :param package_id: `str`, the ID of the CKAN dataset.
        :param resources: `list` of CKAN resources for which Data Qualtiy
            metrics have been calculated.
        :param results: `list` of result `dict`, the results of the calculation
            for each of the resources.
        '''
        self.logger.debug('Cumulative data quality metrics for package: %s',
                          package_id)
        data_quality = self._get_metrics_record('package', package_id)
        if not data_quality:
            data_quality = self._new_metrics_record('package', package_id)
        cumulative = {}
        dataset_results = data_quality.metrics or {}
        for metric in self.metrics:
            cached = dataset_results.get(metric.name, {})
            if cached.get('manual'):
                self.logger.debug('Metric %s is calculated manually. '
                                  'Skipping...', metric.name)
                cumulative[metric.name] = cached
                continue
            metric_results = [res.get(metric.name, {}) for res in results]
            cumulative[metric.name] = metric.calculate_cumulative_metric(
                resources,
                metric_results
            )

        if cumulative != dataset_results:
            data_quality = self._new_metrics_record('package', package_id)

        for metric, result in cumulative.items():
            if result.get('value') is not None:
                setattr(data_quality, metric, result['value'])

        data_quality.metrics = cumulative
        data_quality.modified_at = datetime.now()
        data_quality.save()
        self.logger.debug('Cumulative metrics calculated for: %s', package_id)


class Completeness(DimensionMetric):
    '''Calculates the completeness Data Qualtiy dimension.

    The calculation is performed over all values in the resource data.
    In each row, ever cell is inspected if there is a value present in it.

    The calculation is: `cells_with_value/total_numbr_of_cells * 100`, where:
        * `cells_with_value` is the number of cells containing a value. A cell
            contains a value if the value in the cell is not `None` or an empty
            string or a string containing only whitespace.
        * `total_numbr_of_cells` is the total number of cells expected to be
            populted. This is calculated from the number of rows multiplied by
            the number of columns in the tabular data.

    The return value is a percentage of cells that are populated from the total
    number of cells.
    '''
    def __init__(self):
        super(Completeness, self).__init__('completeness')

    def calculate_metric(self, resource, data):
        '''Calculates the completeness dimension metric for the given resource
        from the resource data.

        :param resource: `dict`, CKAN resource.
        :param data: `dict`, the resource data as a dict with the following
            values:
                * `total`, `int`, total number of rows.
                * `fields`, `list` of `dict`, column metadata - name, type.
                * `records`, `iterable`, iterable over the rows in the resource
                    where each row is a `dict` itself.

        :returns: `dict`, the report contaning the calculated values:
            * `value`, `float`, the percentage of complete values in the data.
            * `total`, `int`, total number of values expected to be populated.
            * `complete`, `int`, number of cells that have value.
        '''
        columns_count = len(data['fields'])
        rows_count = data['total']
        total_values_count = columns_count * rows_count

        self.logger.debug('Rows: %d, Columns: %d, Total Values: %d',
                          rows_count, columns_count, total_values_count)

        total_complete_values = 0
        for row in data['records']:
            total_complete_values += self._completenes_row(row)

        result = \
            float(total_complete_values)/float(total_values_count) * 100.0 if \
            total_values_count else 0
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
        '''Calculates the cumulative report for all resources from the
        calculated results for each resource.

        The calculation is done as `all_complete/all_total * 100`, where
            * `all_complete` is the total number of completed values in all
                resources.
            * all_total is the number of expected values (rows*columns) in all
                resources.
        The final value is the percentage of completed values in all resources
        in the dataset.

        :param resources: `list` of CKAN resources.
        :param metrics: `list` of `dict` results for each resource.

        :returns: `dict`, a report for the total percentage of complete values:
            * `value`, `float`, the percentage of complete values in the data.
            * `total`, `int`, total number of values expected to be populated.
            * `complete`, `int`, number of cells that have value.
        '''
        total, complete = reduce(lambda (total, complete), result: (
            total + result.get('total', 0),
            complete + result.get('complete', 0)
        ), metrics, (0, 0))
        return {
            'total': total,
            'complete': complete,
            'value': float(complete)/float(total) * 100.0 if total else 0.0,
        }


class Uniqueness(DimensionMetric):
    '''Calculates the uniqueness of the data.

    The general calculation is: `unique_values/total_values * 100`, where:
        * `unique_values` is the number of unique values
        * `total_values` is the total number of value

    The dimension value is a percentage of unique values in the data.
    '''
    def __init__(self):
        super(Uniqueness, self).__init__('uniqueness')

    def calculate_metric(self, resource, data):
        '''Calculates the uniqueness of the values in the data for the given
        resource.

        For each column of the data, the number of unique values is calculated
        and the total number of values (basically the number of rows).

        Then, to calculate the number of unique values in the data, the sum of
        all unique values is calculated and the sum of the total number of
        values for each column. The the percentage is calculated from those two
        values.

        :param resource: `dict`, CKAN resource.
        :param data: `dict`, the resource data as a dict with the following
            values:
                * `total`, `int`, total number of rows.
                * `fields`, `list` of `dict`, column metadata - name, type.
                * `records`, `iterable`, iterable over the rows in the resource
                    where each row is a `dict` itself.

        :returns: `dict`, a report on the uniqueness metrics for the given
            resource data:
            * `value`, `float`, the percentage of unique values in the data.
            * `total`, `int`, total number of values in the data.
            * `unique`, `int`, number unique values in the data.
            * `columns`, `dict`, detailed report for each column in the data.
        '''
        total = {}
        distinct = {}

        for row in data['records']:
            for col, value in row.items():
                total[col] = total.get(col, 0) + 1
                if distinct.get(col) is None:
                    distinct[col] = set()
                distinct[col].add(value)

        result = {
            'total': sum(v for _, v in total.items()),
            'unique': sum([len(s) for _, s in distinct.items()]),
            'columns': {},
        }
        if result['total'] > 0:
            result['value'] = (100.0 *
                               float(result['unique'])/float(result['total']))
        else:
            result['value'] = 0.0

        for col, tot in total.items():
            unique = len(distinct.get(col, set()))
            result['columns'][col] = {
                'total': tot,
                'unique': unique,
                'value': 100.0*float(unique)/float(tot) if tot > 0 else 0.0,
            }
        return result

    def calculate_cumulative_metric(self, resources, metrics):
        '''Calculates uniqueness for all resources based on the metrics
        calculated in the previous phase for each resource.

        The calculation is performed based on the total unique values as a
        percentage of the total number of values present in all data from all
        given resources.

        :param resources: `list` of CKAN resources.
        :param metrics: `list` of `dict` results for each resource.

        :returns: `dict`, a report for the total percentage of unique values:
            * `value`, `float`, the percentage of unique values in the data.
            * `total`, `int`, total number of values in the data.
            * `unique`, `int`, number of unique values.
        '''
        result = {}
        result['total'] = sum([r.get('total', 0) for r in metrics])
        result['unique'] = sum([r.get('unique', 0) for r in metrics])
        if result['total'] > 0:
            result['value'] = (100.0 *
                               float(result['unique'])/float(result['total']))
        else:
            result['value'] = 0.0

        return result


class Timeliness(DimensionMetric):
    '''Calculates the timeliness Data Quality dimension.

    The timeliness of a records is the difference between the times when the
    measurement was made and the time that record have entered our system.

    The measurement requires extra configuration - the name of the column in
    the resource data that holds the time of when the measurement was made. If
    this time is missing or the setting is not configured, then the calculation
    cannot be performed automatically.

    The calculation is performed by taking a time delta between the time that
    the resource have been last modified (the time when the data have entered
    and was stored in CKAN) and the time in the specified column, for each
    record.

    The total difference (time delta in resolution of seconds) is then divided
    by the number of records checked, givin the average time delta in seconds.
    This average is then used as the value for this dimension.
    '''
    def __init__(self):
        super(Timeliness, self).__init__('timeliness')

    def calculate_metric(self, resource, data):
        '''Calculates the timeliness of the data in the given resource.

        :param resource: `dict`, CKAN resource. The resource is expected to
            have a property `data_quality_settings` that configures the column
            that holds the timestamp of when the measurement was taken. This
            property is a `dict`, having the following structure:

                .. code-block: python

                    resoruce = {
                        ...
                        'data_quality_settings': {
                            'timeliness': {
                                'column': '<the name of the column',
                            }
                        }
                    }

        :param data: `dict`, the resource data as a dict with the following
            values:
                * `total`, `int`, total number of rows.
                * `fields`, `list` of `dict`, column metadata - name, type.
                * `records`, `iterable`, iterable over the rows in the resource
                    where each row is a `dict` itself.

        :returns: `dict`, a report on the timeliness metrics for the given
            resource data:
            * `value`, `str`, string representation of the average time delta,
                for example: `'+3:24:00'`, `'+3 days, 3:24:00'`
            * `total`, `int`, total number of seconds that the measurements
                have beed delayed.
            * `average`, `int`, the average delay in seocnds.
            * `records`, `int`, number of checked records.
        '''
        settings = resource.get('data_quality_settings', {}).get('timeliness',
                                                                 {})
        column = settings.get('column')
        if not column:
            self.logger.warning('No column for record entry date defined '
                                'for resource %s', resource['id'])
            return {
                'failed': True,
                'error': 'No date column defined in settings',
            }
        dt_format = settings.get('date_format')
        parse_date_column = lambda ds: dateutil.parser.parse(ds)  # NOQA
        if dt_format:
            parse_date_column = lambda ds: datetime.strptime(ds, dt_format)  # NOQA

        created = dateutil.parser.parse(resource.get('last_modified') or
                                        resource.get('created'))

        measured_count = 0
        total_delta = 0

        for row in data['records']:
            value = row.get(column)
            if value:
                try:
                    record_date = parse_date_column(value)
                    if record_date > created:
                        self.logger.warning('Date of record creating is after '
                                            'the time it has entered the '
                                            'system.')
                        continue
                    delta = created - record_date
                    total_delta += delta.total_seconds()
                    measured_count += 1
                except Exception as e:
                    self.logger.debug('Failed to process value: %s. '
                                      'Error: %s', value, str(e))
        if measured_count == 0:
            return {
                'value': '',
                'total': 0,
                'average': 0,
                'records': 0,
            }
        total_delta = round(total_delta)
        avg_delay = timedelta(seconds=int(total_delta/measured_count))

        self.logger.debug('Measured records: %d of %d.',
                          measured_count, data.get('total', 0))
        self.logger.debug('Total delay: %s (%d seconds).',
                          str(total_delta), total_delta)
        self.logger.debug('Average delay: %s (%d seconds).',
                          str(avg_delay), avg_delay.total_seconds())

        return {
            'value': '+%s' % str(avg_delay),
            'total': int(total_delta),
            'average': avg_delay.total_seconds(),
            'records': measured_count,
        }

    def calculate_cumulative_metric(self, resources, metrics):
        '''Calculates the timeliness of all data in all of the given resources
        based on the results for each individual resource.

        The average delay is calculated by getting the total number of seconds
        that all records have been delayed, then dividing that to the number of
        total records in all the data.

        :param resources: `list` of CKAN resources.
        :param metrics: `list` of `dict` results for each resource.

        :returns: `dict`, a report for the timeliness of the data:
            * `value`, `str`, string representation of the average time delta,
                for example: `'+3:24:00'`, `'+3 days, 3:24:00'`
            * `total`, `int`, total number of seconds that the measurements
                have beed delayed.
            * `average`, `int`, the average delay in seocnds.
            * `records`, `int`, number of checked records.
        '''
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
    '''Calculates Data Quality dimension validity.

    The validity is calculated as a percentage of valid records against the
    total number of records in the data.

    The validation is performed using the validation provided by
    https://github.com/frictionlessdata/goodtables-py.
    '''
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
        '''Calculates the percentage of valid records in the resource data.

        The validation of the resource data is done based on the resource
        schema. The schema is specified in the resource metadata itself.

        :param resource: `dict`, CKAN resource.
        :param data: `dict`, the resource data as a dict with the following
            values:
                * `total`, `int`, total number of rows.
                * `fields`, `list` of `dict`, column metadata - name, type.
                * `records`, `iterable`, iterable over the rows in the resource
                    where each row is a `dict` itself.

        :returns: `dict`, a report on the validity metrics for the given
            resource data:
            * `value`, `float`, percentage of valid records in the resource
                data.
            * `total`, `int`, total number of records.
            * `valid`, `int`, number of valid records.
        '''
        validation = None
        try:
            validation = self._perform_validation(resource,
                                                  data.get('total', 0))
        except Exception as e:
            self.logger.error('Failed to validate data for resource: %s. '
                              'Error: %s', resource['id'], str(e))
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
        '''Calculates the percentage of valid records in all the data for the
        given resources based on the calculation for each individual resource.

        The percentage is calculated based on the total number of valid records
        across all of the data in all resources against the total number of
        records in the data.

        :param resources: `list` of CKAN resources.
        :param metrics: `list` of `dict` results for each resource.

        :returns: `dict`, a report on the validity metrics for all of the data.
            * `value`, `float`, percentage of valid records in the data.
            * `total`, `int`, total number of records.
            * `valid`, `int`, number of valid records.
        '''
        total = sum([r.get('total', 0) for r in metrics])
        valid = sum([r.get('valid', 0) for r in metrics])
        if total == 0:
            return {
                'value': 0.0,
                'total': 0,
                'valid': 0,
            }

        return {
            'value': float(valid)/float(total) * 100.0,
            'total': total,
            'valid': valid,
        }


class Accuracy(DimensionMetric):
    '''Calculates Data Qualtiy dimension accuracy.

    Accuracy of a record is determined through background research and it is
    not quite possible to determine if a record is accurate or inaccurate via
    a generic algorithm.

    This metric calculates the percentage of accurate records *only* for
    records that already have been marked as accurate or inaccurate in a
    particular dataset.

    To calculate this, the record must contain a flag, a column in the dataset,
    that marks the record as accurate, inaccurate or not determined.

    If such column is present, then the calculation is:
    `number_of_accurate/(number_of_accurate + number_of_inaccurate) * 100)`.

    Accuracy is measured as percentage of accurate records, from the set of
    records that have been checked and marked as accurate or inaccurate.
    '''
    def __init__(self):
        super(Accuracy, self).__init__('accuracy')

    def calculate_metric(self, resource, data):
        '''Calculates the percentage of accurate records for the given resource
        data.

        The resource must contain a data quality setting to configure which
        column contains the flag that marks the record as accurate.

        :param resource: `dict`, CKAN resource. The resource dict must contain
            a property `data_quality_settings` which contain the name of the
            column used to determine the accuracy of that record. This
            property must have the following format:

                .. code-block: python

                    resource = {
                        ...
                        'data_quality_settings': {
                            'accuracy': {
                                'column': '<column name>',
                            }
                        }
                    }
        :param data: `dict`, the resource data as a dict with the following
            values:
                * `total`, `int`, total number of rows.
                * `fields`, `list` of `dict`, column metadata - name, type.
                * `records`, `iterable`, iterable over the rows in the resource
                    where each row is a `dict` itself.

        :returns: `dict`, a report on the accuracy metrics for the resource
            data:
            * `value`, `float`, percentage of accurate records in the data.
            * `accurate`, `int`, number of accurate records.
            * `inaccurate`, `int`, number of inaccurate records.
            * `total`, `int`, `accurate` + `inaccurate` - total number of
                checked records.
        '''
        settings = resource.get('data_quality_settings',
                                {}).get('accuracy', {})
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
        '''Calculates the percentage of accurate records in all data for the
        given resources, based on the calculations for individual resources.

        The value is calculated as percentage of accurate records of the total
        number of checked records (all accurate + all inaccurate records).

        :param resources: `list` of CKAN resources.
        :param metrics: `list` of `dict` results for each resource.

        :returns: `dict`, a report on the accuracy metrics for all data in all
            resources:
            * `value`, `float`, percentage of accurate records in the data.
            * `accurate`, `int`, number of accurate records.
            * `inaccurate`, `int`, number of inaccurate records.
            * `total`, `int`, `accurate` + `inaccurate` - total number of
                checked records.
        '''
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
    '''Calculates Data Quality dimension consistency.

    This dimension gives a metric of how consistent are the values of same type
    accross the dataset (or resource).

    The type of the values is determined by the type of the column in CKAN's
    data store (like int, numeric, timestamp, text etc).
    For each type, a validator for the consistency is used to try to categorize
    the value in some category - for example all dates with same formats would
    be in the same category, all numbers that use the same format, how many
    of the numbers in a column are floating point and how many are integer.

    For each column, we may get multiple categories (plus a special category
    called `unknown` which means we could not determine the category for those
    values), and we count the number of values for each category.
    The consistency, for a given column, would be the number of values in the
    category with most values, expressed as a percentage of the total number of
    values in that column.

    To calculate the consistency for the whole data, we calculate the total
    number of consistent values (sum of all columns) expressed as a percentage
    of the total number of values present in the data.
    '''
    def __init__(self):
        super(Consistency, self).__init__('consistency')

    def validate_date(self, field, value, _type, report):
        date_format = detect_date_format(value) or 'unknown'
        formats = report['formats']
        formats[date_format] = formats.get(date_format, 0) + 1

    def validate_numeric(self, field, value, _type, report):
        num_format = detect_numeric_format(value) or 'unknown'
        formats = report['formats']
        formats[num_format] = formats.get(num_format, 0) + 1

    def validate_int(self, field, value, _type, report):
        num_format = detect_numeric_format(value) or 'unknown'
        formats = report['formats']
        formats[num_format] = formats.get(num_format, 0) + 1

    def validate_string(self, field, value, _type, report):
        formats = report['formats']
        formats[_type] = formats.get(_type, 0) + 1

    def get_consistency_validators(self):
        return {
            'timestamp': self.validate_date,
            'numeric': self.validate_numeric,
            'int': self.validate_int,
            'string': self.validate_string,
            'text': self.validate_string,
        }

    def calculate_metric(self, resource, data):
        '''Calculates the consistency of the resource data.

        For each of the columns of the resource data, we determine the number
        of values that belong in the same category (have the same format, are
        of exactly the same type, etc). Then, we find the category with most
        values, per column, and use that expressed as percentage to calculate
        the consistency for that column.
        The final value is calculated from the results obtained for each
        column.

        :param resource: `dict`, CKAN resource.
        :param data: `dict`, the resource data as a dict with the following
            values:
                * `total`, `int`, total number of rows.
                * `fields`, `list` of `dict`, column metadata - name, type.
                * `records`, `iterable`, iterable over the rows in the resource
                    where each row is a `dict` itself.

        :returns: `dict`, a report on the consistency metrics the date in the
            resource:
            * `value`, `float`, percentage of consistent records in the data.
            * `consistent`, `int`, number of consistent records.
            * `total`, `int`, total number ofrecords.
            * `report`, `dict`, detailed, per column, report for the
                consistency of the data.
        '''
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
            most_consistent = max([count if fmt != 'unknown' else 0
                                   for fmt, count
                                   in field_report['formats'].items()])
            field_report['consistent'] = most_consistent

        total = sum([f.get('count', 0) for _, f in report.items()])
        consistent = sum([f.get('consistent', 0) for _, f in report.items()])
        value = float(consistent)/float(total) * 100.0 if total else 0.0
        return {
            'total': total,
            'consistent': consistent,
            'value': value,
            'report': report,
        }

    def calculate_cumulative_metric(self, resources, metrics):
        '''Calculates the total percentage of consistent values in the data for
        all the given resources.

        :param resources: `list` of CKAN resources.
        :param metrics: `list` of `dict` results for each resource.

        :returns: `dict`, a report on the consistency metrics the date in the
            resource:
            * `value`, `float`, percentage of consistent records in the data.
            * `consistent`, `int`, number of consistent records.
            * `total`, `int`, total number ofrecords.
            * `report`, `dict`, detailed, per column, report for the
                consistency of the data.
        '''
        total = sum([r.get('total', 0) for r in metrics])
        consistent = sum([r.get('consistent', 0) for r in metrics])

        # FIXME: This is not the proper calculation. We need to merge all
        # data to calculate the consistency properly.
        value = float(consistent)/float(total) * 100.0 if total else 0.0
        return {
            'total': total,
            'consistent': consistent,
            'value': value,
        }


# Date format utils

_all_date_formats = [
    '%Y-%m-%d',
    '%y-%m-%d',
    '%Y/%m/%d',
    '%y/%m/%d',
    '%Y.%m.%d',
    '%y.%m.%d',
    '%d-%m-%Y',
    '%d-%m-%y',
    '%d/%m/%Y',
    '%d/%m/%y',
    '%d.%m.%Y',
    '%d.%m.%y',
    '%m-%d-%Y',
    '%m-%d-%y',
    '%m/%d/%Y',
    '%m/%d/%y',
    '%m.%d.%Y',
    '%m.%d.%y',
]


def _generate_time_formats():
    additional = []
    for time_sep in ['T', ' ', ', ', '']:
        if time_sep:
            for date_fmt in _all_date_formats:
                for time_fmt in ['%H:%M:%S',
                                 '%H:%M:%S.%f',
                                 '%H:%M:%S.%fZ',
                                 '%H:%M:%S.%f%Z',
                                 '%H:%M:%S.%f%z']:
                    additional.append(date_fmt + time_sep + time_fmt)
    return additional


_all_date_formats += _generate_time_formats()


_all_numeric_formats = [
    r'^\d+$',
    r'^[+-]\d+$',
    r'^(\d{1,3},)+(\d{3})$',
    r'^(\d{1,3},)+(\d{3})\.\d+$',
    r'^[+-](\d{1,3},)(\d{3})+$',
    r'^[+-](\d{1,3},)+(\d{3})\.\d+$',
    r'^\d+\.\d+$',
    r'^[+-]\d+\.\d+$',
]


def detect_date_format(datestr):
    '''Tries to detect the date-time format from the given date or timestamp
    string.

    :param datestr: `str`, the date string

    :returns: `str`, the guessed format of the date, otherwise `None`.
    '''
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
    '''Tries to detect the format of a number (int, float, number format with
    specific separator such as comma "," etc).

    :param numstr: `str`, `int`, `float`, the number string (or numeric value)
        to try to guess the format for.

    :returns: `str`, the guessed number format, otherwise `None`.
    '''
    for parser in [int, float]:
        try:
            parser(numstr)
            return parser.__name__
        except:
            pass

    for num_format in _all_numeric_formats:
        m = re.match(num_format, str(numstr))
        if m:
            return num_format
    return None


# resource validation
def validate_resource_data(resource):
    '''Performs a validation of a resource data, given the resource metadata.

    :param resource: CKAN resource data_dict.

    :returns: `dict`, a validation report for the resource data.
    '''
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
                toolkit.config.get(u'ckanext.validation.pass_auth_header',
                                   True))
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
    site_user_name = toolkit.get_action('get_site_user')({
        'ignore_auth': True
    }, {})
    site_user = toolkit.get_action('get_site_user')(
        {'ignore_auth': True}, {'id': site_user_name})
    return site_user['apikey']
