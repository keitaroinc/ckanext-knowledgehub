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

'''User interests service.
'''
import json
from ckan.lib.redis import connect_to_redis
import ckan.model as model
from ckan.common import config
from ckan.plugins import toolkit as toolkit
from ckan.lib.dictization import table_dictize

from ckanext.knowledgehub.model.user_profile import UserProfile
from ckanext.knowledgehub.model.query import UserQueryResult
from logging import getLogger


log = getLogger(__name__)


class UserProfileService:
    '''Service that manages user profile data such as interests and most recent
    relevant searches.

    It uses caching (in Redis) to store temporary user interests.

    :param redis: The redis connection. If ommited, the default CKAN Redis
        connection will be used
    :param user_profile: `UserProfile`, model to be used for accessing the
        user profile data
    :param user_ques_result: `UserQueryResult`, model to be used for accessing
        the relevant user queries.
    '''

    PROFILE_CACHE_PREFIX = 'ckanext.knowledgehub.user.profile'
    # Cache timeout - default to 5 minutes
    CACHE_TIMEOUT = config.get('ckanext.knowledgehub.cache_timeout', 5*60)
    RELEVANT_SEARCHES = config.get('ckanext.knowledgehub.relevant_searches', 5)

    def __init__(self, redis=None, user_profile=UserProfile,
                 user_query_result=UserQueryResult):
        self.redis = redis or connect_to_redis
        self.user_profile = user_profile
        self.user_query_result = user_query_result

    def _get_key(self, user_id, suffix=None):
        if suffix:
            return '%s.%s:%s' % (UserProfileService.PROFILE_CACHE_PREFIX,
                                 suffix, user_id)
        return '%s:%s' % (UserProfileService.PROFILE_CACHE_PREFIX, user_id)

    def _connect(self):
        return self.redis()

    def get_profile(self, user_id):
        '''Returns the user profile as a dict.

        :param user_id: `str`, the user id.

        :returns: `dict`, the user profile data.
        '''
        profile = self.user_profile.by_user_id(user_id)
        if not profile:
            return None
        context = {
            'model': model,
            'session': model.Session,
        }
        profile = table_dictize(profile, context)

        return profile

    def get_interests(self, user_id):
        '''Returns the user interests as a dict.

        :param user_id: `str`, the user id.

        :returns: `dict`, the user interests as set in the user profile.
        '''
        profile = self.get_profile(user_id) or {}
        return profile.get('interests')

    def get_interests_boost(self, user_id):
        '''Returns the interests to be used as boost parameters in the queries
        to the Solr indexer.

        The response dict contains the names and the values of the fields that
        should be boosted alog with the coefficient of boosting. For example:

            .. code-block: json

                {
                    "normal": {
                        "idx_keywords": ["k1", "k2"]  // boost idx_keywords
                                                      // with standard boost
                    },
                    "^0.5": {
                        "idx_keywords": ["k3", "k4"]  // boost with coeff 0.5
                                                      // when idx_keywords has
                                                      // value k3 or k4
                    }
                }
        '''
        try:
            conn = self._connect()
            cached = conn.get(self._get_key(user_id, 'boost_params'))
            if cached:
                return json.loads(cached)
        except Exception as e:
            log.warning('Failed to check cache. Error: %s', str(e))
            lo.exception(e)
            return {}

        interests = self.get_interests(user_id) or {}

        relevant = self.get_last_relevant(user_id)

        searches = {}
        for k, values in relevant.items():
            searches[k] = []
            for v in values:
                if v not in interests.get(k, []):
                    searches[k].append(v)

        values = {
            'normal': {
                'idx_keywords': sorted(interests.get('keywords', [])),
                'idx_tags': sorted(interests.get('tags', [])),
                'idx_research_questions': sorted(
                    interests.get('research_questions', [])),
            },
            '^0.5': {
                'idx_keywords': sorted(searches.get('keywords', [])),
                'idx_tags': sorted(searches.get('tags', [])),
                'idx_research_questions': sorted(
                    searches.get('research_questions', [])),
            }
        }

        try:
            conn.setex(self._get_key(user_id, 'boost_params'),
                       json.dumps(values),
                       UserProfileService.CACHE_TIMEOUT)
        except Exception as e:
            log.warning('Failed to store in cache. Error: %s', str(e))
            log.exception(e)

        return values

    def get_last_relevant(self, user_id):
        '''Returns the last relevant tags, keywords and research questions from
        the user queries in the system.
        '''
        relevant = {
            'tags': set(),
            'keywords': set(),
            'research_questions': set(),
        }

        def _action(action_name, context, data_dict):
            try:
                return toolkit.get_action(action_name)(context, data_dict)
            except Exception as e:
                log.warning('Failed to execute %s. Error: %s',
                            action_name, str(e))
            return None

        keywords = set()

        for package_id in self.user_query_result.get_last_relevant(
                user_id,
                'dataset',
                UserProfileService.RELEVANT_SEARCHES):
            package = _action('package_show', {
                'ignore_auth': True,
            }, {
                'id': package_id
            })
            if package:
                for tag in package.get('tags', []):
                    relevant['tags'].add(tag['name'])
                    if tag.get('keyword_id'):
                        keywords.add(tag['keyword_id'])

                for keyword in package.get('keywords', []):
                    keywords.add(keyword)

        for rq in self.user_query_result.get_last_relevant(
                user_id,
                'research_question',
                UserProfileService.RELEVANT_SEARCHES):
            relevant['research_questions'].add(rq)

        for dashboard in self.user_query_result.get_last_relevant(
                user_id,
                'dashboard',
                UserProfileService.RELEVANT_SEARCHES):
            dashboard = _action('dashboard_show', {
                'ignore_auth': True
            }, {
                'id': dashboard
            })
            if dashboard and dashboard.get('tags'):
                for tag in dashboard['tags'].split(','):
                    tag = _action('tag_show', {
                        'ignore_auth': True
                    }, {
                        'id': tag
                    })
                    if tag:
                        relevant['tags'].add(tag['name'])
                        if tag.get('keyword_id') is not None:
                            keywords.add(tag['keyword_id'])

        for keyword in keywords:
            keyword = _action('keyword_show', {
                'ignore_auth': True
            }, {
                'id': keyword
            })
            if keyword:
                relevant['keywords'].add(keyword['name'])

        return relevant

    def clear_cached(self, user_id):
        '''Clears the cached parameters for this user.

        :param user_id: `str`, the user id for which to clear the cache.
        '''
        self.redis().delete(self._get_key(user_id, 'boost_params'))

user_profile_service = UserProfileService()
