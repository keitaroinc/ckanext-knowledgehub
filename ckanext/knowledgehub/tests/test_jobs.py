"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from mock import Mock, MagicMock

from ckanext.knowledgehub.lib.util import monkey_patch
from ckanext.knowledgehub.logic.jobs import (
    calculate_metrics,
    schedule_data_quality_check,
    IndexedModelsRefreshIndex,
    DatasetIndexRefresh,
    update_index,
    update_dashboard_index,
    schedule_update_index,
    schedule_notification_email,
    schedule_broadcast_notification_email,
)
from ckanext.knowledgehub.lib.email import (
    send_notification_email
)
from ckanext.knowledgehub.lib import quality
import ckanext.knowledgehub.helpers as kwn_helpers
import ckan.lib.jobs as jobs
import ckan.lib.search as ckan_search

import nose.tools


assert_equals = nose.tools.assert_equals
assert_true = nose.tools.assert_true


class TestMetrics:

    @monkey_patch(quality.DataQualityMetrics,
                  'calculate_metrics_for_dataset',
                  Mock())
    def test_calculate_metrics(self):
        calculate_metrics('pkg-001')
        quality.DataQualityMetrics.calculate_metrics_for_dataset.\
            assert_called_once_with('pkg-001')

    @monkey_patch(jobs, 'enqueue', Mock())
    def test_schedule_data_quality_check(self):
        schedule_data_quality_check('pkg-001')
        jobs.enqueue.assert_called_once_with(calculate_metrics,
                                             ['pkg-001', False])


class TestModelIndexRefresh:

    def test_find_documents(self):
        model = MagicMock()
        index = IndexedModelsRefreshIndex(model)

        docs = [{'id': 'doc-1'}]

        model.search_index.return_value = docs

        result = index.find_documents('test-query')

        assert_true(result is not None)
        assert_equals(result, ['doc-1'])  # return just the ID's of the docs

        model.search_index.assert_called_once_with(q='text:"test-query"')

    def test_refresh_index_for(self):

        class _DocModel:

            @classmethod
            def get(cls, ref):
                pass

            @classmethod
            def update_index_doc(cls, doc):
                pass

        _DocModel.get = Mock()
        _DocModel.update_index_doc = Mock()

        dummy = _DocModel()
        _DocModel.get.return_value = dummy
        _DocModel.update_index_doc.return_value = dummy

        index = IndexedModelsRefreshIndex(_DocModel)

        result = index.refresh_index_for('doc-1')

        assert_true(result is not None)
        assert_equals(result, dummy)

        _DocModel.get.assert_called_once_with('doc-1')
        _DocModel.update_index_doc.assert_called_once_with(dummy.__dict__)

    def test_refresh_index(self):
        model = MagicMock()

        index = IndexedModelsRefreshIndex(model)
        index.find_documents = Mock()
        index.refresh_index_for = Mock()

        index.find_documents.return_value = ['doc-1']
        index.refresh_index_for.return_value = {'id': 'doc-1'}

        index.refresh_index('test-query')

        index.find_documents.assert_called_once_with('test-query')
        index.refresh_index_for.assert_called_once_with('doc-1')

    @monkey_patch(ckan_search, 'rebuild', Mock())
    def test_dataset_refresh_index(self):
        index = DatasetIndexRefresh()
        index.find_documents = Mock()
        index.find_documents.return_value = ['doc-1']

        index.refresh_index('test-query')

        index.find_documents.assert_called_once_with('test-query')
        ckan_search.rebuild.assert_called_once_with(package_id='doc-1')

    @monkey_patch(IndexedModelsRefreshIndex, 'refresh_index', Mock())
    @monkey_patch(DatasetIndexRefresh, 'refresh_index', Mock())
    def test_update_index_global(self):
        update_index('test-query')

        assert_equals(IndexedModelsRefreshIndex.refresh_index.call_count, 3)
        DatasetIndexRefresh.refresh_index.assert_called_once_with('test-query')


class TestScheduleJobs:

    @monkey_patch(jobs, 'enqueue', Mock())
    def test_schedule_update_index(self):
        schedule_update_index('test-query')
        jobs.enqueue.assert_called_once_with(update_index, ['test-query'])

    @monkey_patch(jobs, 'enqueue', Mock())
    def test_schedule_notification_email(self):
        data = {'test': 'value'}
        schedule_notification_email('rec', 'template_name', data)
        jobs.enqueue.assert_called_once_with(send_notification_email, [
            'rec',
            'template_name',
            data,
        ])

    @monkey_patch(kwn_helpers, 'get_members', Mock())
    @monkey_patch(jobs, 'enqueue', Mock())
    def test_schedule_broadcast_notification_email(self):
        kwn_helpers.get_members.return_value = [('user1', None, None),
                                                ('user2', None, None)]

        schedule_broadcast_notification_email('grp1', 'templ_name', {
            'test': 'value',
        })

        assert_equals(kwn_helpers.get_members.call_count, 1)
        assert_equals(jobs.enqueue.call_count, 2)
