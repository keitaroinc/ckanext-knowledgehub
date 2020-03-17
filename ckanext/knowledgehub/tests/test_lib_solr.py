from mock import Mock, patch, MagicMock

from ckan.tests import helpers
from ckan.plugins import toolkit
from ckan.common import config
from pysolr import Results

from ckanext.knowledgehub.lib.solr import (
    Index,
    Indexed,
    ckan_params_to_solr_args,
    mapped,
    unprefixed,
    to_indexed_doc,
    indexed_doc_to_data_dict,
    )

from nose.tools import (
    assert_true,
    assert_equals,
    raises,
)


class TestIndex(helpers.FunctionalTestBase):

    def test_search(self):
        solr_conn_mock = Mock()
        index = Index()
        index.get_connection = Mock()

        index.get_connection.return_value = solr_conn_mock

        solr_conn_mock.search.return_value = Results({
            'response': {
                'docs': [{
                    'id': 'aaa',
                    'p1': 'v1',
                    'p2': 'v2',
                }],
                'numFound': 1,
            }
        })

        query = {
            'q': 'id:aaa',
            'fq': {
                'p1': 'v1',
                'p2': 'v2',
            }
        }
        results = index.search('test_doc', **query)

        solr_conn_mock.search.assert_called_once_with(**{
            'q': 'id:aaa',
            'fq': ['p1:v1', 'p2:v2', 'entity_type:test_doc'],
            'rows': 500,
        })

        assert_true(results is not None)
        assert_equals(len(results.docs), 1, 'Expected at least 1 result')

    def test_search_all_args(self):
        solr_conn_mock = Mock()
        index = Index()
        index.get_connection = Mock()

        index.get_connection.return_value = solr_conn_mock

        solr_conn_mock.search.return_value = Results({
            'response': {
                'docs': [{
                    'id': 'aaa',
                    'p1': 'v1',
                    'p2': 'v2',
                }],
                'numFound': 1,
            }
        })

        query = {
            'q': 'id:aaa',
            'fq': {
                'p1': 'v1',
                'p2': 'v2',
            },
            'rows': 10,
            'start': 4,
            'sort': 'qsort'
        }
        results = index.search('test_doc', **query)

        solr_conn_mock.search.assert_called_once_with(**{
            'q': 'id:aaa',
            'fq': ['p1:v1', 'p2:v2', 'entity_type:test_doc'],
            'rows': 10,
            'start': 4,
            'sort': 'qsort'
        })

        assert_true(results is not None)
        assert_equals(len(results.docs), 1, 'Expected at least 1 result')

    def test_add(self):
        solr_conn_mock = Mock()
        index = Index()
        index.get_connection = Mock()

        index.get_connection.return_value = solr_conn_mock

        doc = {
            'p1': 'v1',
            'p2': 'v2',
        }

        index.add('test_doc', doc)

        solr_conn_mock.add.assert_called_once_with([{
            'p1': 'v1',
            'p2': 'v2',
            'entity_type': 'test_doc'
        }], commit=True)

    def test_remove(self):
        solr_conn_mock = Mock()
        index = Index()
        index.get_connection = Mock()

        index.get_connection.return_value = solr_conn_mock

        index.remove('test_doc', p1='v1', p2='v2')

        solr_conn_mock.delete.assert_called_once_with(
            q='entity_type:test_doc AND p1:v1 AND p2:v2',
            commit=True)

    def test_remove_all(self):
        solr_conn_mock = Mock()
        index = Index()
        index.get_connection = Mock()

        index.get_connection.return_value = solr_conn_mock

        index.remove_all('test_doc')

        solr_conn_mock.delete.assert_called_once_with(
            q='entity_type:test_doc',
            commit=True)


class TestHelperMethods(helpers.FunctionalTestBase):

    def test_ckan_params_to_solr_args(self):
        args = ckan_params_to_solr_args({
            'q': {
                'p1': 'v1',
                'p2': 'v2',
            },
            'fq': {
                'f1': 'v1',
                'f2': 'v2',
            }
        })

        assert_equals({
            'q': 'p1:"v1" AND p2:"v2"',
            'fq': {
                'f1': 'v1',
                'f2': 'v2',
            }
        }, args)

    def test_mapped(self):
        result = mapped('prop', 'alias_prop')
        assert_equals({
            'field': 'prop',
            'as': 'alias_prop',
        }, result)

    def test_unprefixed(self):
        result = unprefixed('prop')
        assert_equals({
            'field': 'prop',
            'as': 'prop',
        }, result)

    def test_to_indexed_doc(self):
        from hashlib import md5
        site_id = config.get('ckan.site_id')
        index_id = md5('test_doc:aaa').hexdigest()
        result = to_indexed_doc({
            'id': 'aaa',
            'title': 'Test',
            'name': 'test',
            'prop': 'value',
            'other': 'should be ignored',
        }, 'test_doc', [
            {'field': 'id', 'as': 'id'},
            'name',
            'title',
            {'field': 'prop', 'as': 'pref_prop'}
        ])

        assert_equals({
            'id': 'aaa',
            'title': 'Test',
            'name': 'test',
            'pref_prop': 'value',
            'entity_type': 'test_doc',
            'site_id': site_id,
            'index_id': index_id,
        }, result)

    def test_indexed_doc_to_data_dict(self):
        data = indexed_doc_to_data_dict({
            'id': 'aaa',
            'title': 'Test',
            'name': 'test',
            'pref_prop': 'value',
            'entity_type': 'test_doc',
            'site_id': 'test.site',
            'index_id': 'mock-index-id',
        }, [
            {'field': 'id', 'as': 'id'},
            'name',
            'title',
            {'field': 'prop', 'as': 'pref_prop'}
        ])

        assert_equals({
            'id': 'aaa',
            'title': 'Test',
            'name': 'test',
            'prop': 'value',
        }, data)


def model(data, model_name='_MockModel'):
    from collections import namedtuple
    mock_model = namedtuple(model_name, sorted(data))
    return mock_model(**data)


class TestIndexedMixin(helpers.FunctionalTestBase):

    def _get_mixin_class(self):

        class IndexedDataModel(Indexed):
            indexed = ['id', 'title', 'name', 'description', 'property']
            doctype = 'test_doc'
            Session = MagicMock()
            index = MagicMock()

        return IndexedDataModel

    def test_rebuild_index(self):
        cls = self._get_mixin_class()

        state = {'call': 0}

        def _query_db(*args, **kwargs):
            if state['call']:
                return []
            state['call'] += 1
            return [
                model({
                    'id': 'aaa',
                    'title': 'Test Model',
                    'name': 'test-model',
                    'description': 'Test Description',
                }),
            ]

        cls.Session.query().offset().limit().all.side_effect = _query_db

        cls.rebuild_index()

        assert_equals(2, cls.Session.query().offset().limit().all.call_count)
        cls.index.remove_all.assert_called_once_with('test_doc')
        cls.index.add.assert_called_once()

    def test_add_to_index(self):
        cls = self._get_mixin_class()

        def _add(doctype, doc):
            assert_equals('test_doc', doctype)
            assert_true(doc)
            assert_true(doc.get('khe_id'))
            assert_true(doc.get('title'))
            assert_true(doc.get('name'))
            assert_true(doc.get('khe_description'))
            assert_true(doc.get('site_id'))
            assert_true(doc.get('index_id'))
            assert_equals('test_doc', doc.get('entity_type'))

        cls.index.add.side_effect = _add

        cls.add_to_index({
            'id': 'aaa',
            'title': 'Test Model',
            'name': 'test-model',
            'description': 'Test Description',
        })

        cls.index.add.assert_called_once()

    def test_update_index_doc(self):
        cls = self._get_mixin_class()

        cls.index.search.return_value = Results({
            'response': {
                'docs': [{
                    'khe_id': 'aaa',
                    'title': 'Test Model',
                    'name': 'test-model',
                    'khe_description': 'Test Description',
                    'site_id': 'test',
                    'entity_type': 'test_doc',
                    'index_id': '1',
                }],
                'numFound': 1,
            }
        })

        def _add(doctype, doc):
            assert_equals('test_doc', doctype)
            assert_true(doc)
            assert_true(doc.get('khe_id'))
            assert_true(doc.get('title'))
            assert_true(doc.get('name'))
            assert_true(doc.get('khe_description'))
            assert_true(doc.get('site_id'))
            assert_true(doc.get('index_id'))
            assert_equals('test_doc', doc.get('entity_type'))

        cls.index.add.side_effect = _add

        cls.update_index_doc({
            'id': 'aaa',
            'title': 'Test Model',
            'name': 'test-model',
            'description': 'Test Description',
        })

        cls.index.search.assert_called_once_with('test_doc', q='khe_id:aaa')
        cls.index.remove.assert_called_once_with('test_doc', khe_id='aaa')
        cls.index.add.assert_called_once()

    @raises(toolkit.ValidationError)
    def test_validate_solr_args(self):
        cls = self._get_mixin_class()

        try:
            cls.validate_solr_args({
                'q': 'test',
                'fq': 'test',
                'rows': 10,
                'start': 2,
                'sort': 'test',
                'df': 'test',
                'fl': 'test',
            })
        except Exception as e:
            raise Exception('Did not expected this to fail. Error: ' + e)

        cls.validate_solr_args({
            'q': 'test',
            'fq': 'test',
            'rows': 10,
            'start': 2,
            'sort': 'test',
            'df': 'test',
            'fl': 'test',
            'invalid': 'invalid arg',
        })

    def test_search_index(self):
        cls = self._get_mixin_class()

        cls.index.search.return_value = Results({
            'response': {
                'docs': [{
                    'khe_id': 'aaa',
                    'title': 'Test Model',
                    'name': 'test-model',
                    'khe_description': 'Test Description',
                    'site_id': 'test',
                    'entity_type': 'test_doc',
                    'index_id': '1',
                }],
                'numFound': 1,
            }
        })

        results = cls.search_index(
            q={'p1': 'v1'},
            fq={'f1': 'v1'},
            rows=10, start=3,
            sort='test_sort')
        assert_true(results is not None)
        cls.index.search.assert_called_once_with(
            'test_doc',
            q={'p1': 'v1'},
            fq={'f1': 'v1'},
            rows=10,
            start=3,
            sort='test_sort')

    def test_delete_from_index(self):
        cls = self._get_mixin_class()
        cls.delete_from_index({
            'id': 'aaa',
        })
        cls.index.remove.assert_called_once_with('test_doc', khe_id='aaa')

        cls = self._get_mixin_class()
        cls.delete_from_index('aaa')
        cls.index.remove.assert_called_once_with('test_doc', khe_id='aaa')
