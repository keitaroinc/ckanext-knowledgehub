from mock import Mock, patch, MagicMock

from ckanext.knowledgehub.lib.profile import UserProfileService
from ckanext.knowledgehub.model.user_profile import UserProfile
from ckanext.knowledgehub.lib.util import monkey_patch
from ckan.plugins import toolkit as toolkit

from nose.tools import (
    assert_true,
    assert_equals,
    raises,
)


class TestUserProfileService:

    def test_get_profile(self):
        user_profile_mock = MagicMock()
        service = UserProfileService(redis=MagicMock(),
                                     user_profile=user_profile_mock,
                                     user_query_result=MagicMock())

        user_profile_mock.by_user_id.return_value = UserProfile()

        profile = service.get_profile('user-001')
        assert_true(profile is not None)

    def test_get_interests(self):
        service = UserProfileService(redis=MagicMock(),
                                     user_profile=MagicMock(),
                                     user_query_result=MagicMock())
        service.get_profile = Mock()
        interests = {
            'tags': ['tag1', 'tag2'],
            'keywords': ['keyword1', 'keyword2'],
            'research_questions': ['rq1', 'rq2'],
        }
        service.get_profile.return_value = {
            'interests': interests,
        }

        result = service.get_interests('user-001')
        assert_true(result is not None)
        assert_equals(result, interests)
        service.get_profile.assert_called_once_with('user-001')

    @monkey_patch(toolkit, 'get_action', MagicMock())
    def test_get_last_relevant(self):
        datasets = {
            'pkg1': {
                'tags': [{'id': 't1', 'name': 't1', 'keyword_id': 'k1'}],
                'keywords': ['k1']
            },
            'pkg2': {
                'tags': [{'id': 't2', 'name': 't2'}]
            },
            'pkg3': {},
            'pkg4': {
                'tags': [{'id': 't3', 'name': 't3', 'keyword_id': 'k3'}],
                'keywords': ['k3']
            },
            'pkg5': {
                'tags': [{'id': 't1', 'name': 't1', 'keyword_id': 'k1'}],
                'keywords': ['k1']
            },
        }

        tags = {
            't1': {'id': 't1', 'name': 't1', 'keyword_id': 'k1'},
            't2': {'id': 't2', 'name': 't2'},
            't3': {'id': 't3', 'name': 't3', 'keyword_id': 'k3'},
            't4': {'id': 't4', 'name': 't4', 'keyword_id': 'k4'},
            't5': {'id': 't5', 'name': 't5', 'keyword_id': 'k4'},
        }

        keywords = {
            'k1': {'id': 'k1', 'name': 'k1'},
            'k2': {'id': 'k2', 'name': 'k2'},
            'k3': {'id': 'k3', 'name': 'k3'},
            'k4': {'id': 'k4', 'name': 'k4'},
        }

        dashboards = {
            'd1': {'id': 'd1', 'tags': 't1,t3'},
            'd2': {'id': 'd2', 'tags': 't2,t3'},
            'd3': {'id': 'd3', 'tags': 't4,t5'},
        }

        def _get(col, key):
            if key not in col:
                raise Exception('Not found: ' + str(key))
            return col[key]

        _actions = {
            'package_show': lambda ctx, dd: _get(datasets, dd['id']),
            'tag_show': lambda ctx, dd: _get(tags, dd['id']),
            'keyword_show': lambda ctx, dd: _get(keywords, dd['id']),
            'dashboard_show': lambda ctx, dd: _get(dashboards, dd['id']),
        }

        def _get_action(action):
            return _actions[action]

        toolkit.get_action.side_effect = _get_action

        user_query_result_mock = MagicMock()

        def _get_last_relevant_mock(user_id, _type, _max):
            if _type == 'dataset':
                return ['pkg1', 'pkg2', 'pkg3', 'pkg4', 'pkg5']
            elif _type == 'research_question':
                return ['rq1', 'rq2', 'rq3']
            elif _type == 'dashboard':
                return ['d1', 'd2', 'd3']
            raise Exception('Invalid type: ' + _type)

        user_query_result_mock.get_last_relevant.side_effect = \
            _get_last_relevant_mock

        service = UserProfileService(redis=MagicMock(),
                                     user_profile=MagicMock(),
                                     user_query_result=user_query_result_mock)

        relevant = service.get_last_relevant('user-001')
        assert_true(relevant is not None)
        assert_equals(relevant, {
            'research_questions': set(['rq1', 'rq2', 'rq3']),
            'keywords': set(['k1', 'k3', 'k4']),
            'tags': set(['t1', 't2', 't3', 't4', 't5'])
        })

    def test_interests_boost(self):
        redis_mock = MagicMock()

        redis_mock.get.return_value = None

        service = UserProfileService(redis_mock, MagicMock(), MagicMock())

        interests = {
            'keywords': ['k1', 'k2'],
            'tags': ['t1', 't2'],
            'research_questions': ['rq1', 'rq2'],
        }

        searches = {
            'keywords': set(['k3', 'k4']),
            'tags': set(['t3', 't4']),
            'research_questions': set(['rq3', 'rq4']),
        }

        service.get_interests = Mock()
        service.get_last_relevant = Mock()

        service.get_interests.return_value = interests
        service.get_last_relevant.return_value = searches

        result = service.get_interests_boost('user-001')

        assert_true(result is not None)
        assert_equals(result, {
            'normal': {
                'idx_keywords': ['k1', 'k2'],
                'idx_tags': ['t1', 't2'],
                'idx_research_questions': ['rq1', 'rq2'],
            },
            '^0.5': {
                'idx_keywords': ['k3', 'k4'],
                'idx_tags': ['t3', 't4'],
                'idx_research_questions': ['rq3', 'rq4'],
            }
        })
        assert_equals(redis_mock.setex.call_count, 1)
