'''User interests service.
'''
import json
from ckan.lib.redis import connect_to_redis
import ckan.model as model
from ckan.plugins import toolkit as toolkit
from ckan.lib.dictization import table_dictize

from ckanext.knowledgehub.model.user_profile import UserProfile
from ckanext.knowledgehub.model.query import UserQueryResult
from logging import getLogger


log = getLogger(__name__)


class UserProfileService:

    PROFILE_CACHE_PREFIX = 'ckanext.knowledgehub.user.profile'
    CACHE_TIMEOUT = 5*60  # 5 minutes

    def __init__(self, redis=None, user_profile=UserProfile,
                 user_query_result=UserQueryResult):
        self.redis = redis or connect_to_redis()
        self.user_profile = user_profile
        self.user_query_result = user_query_result

    def _get_key(self, user_id, suffix=None):
        if suffix:
            return '%s.%s:%s' % (UserProfileService.PROFILE_CACHE_PREFIX, suffix, user_id)
        return '%s:%s' % (UserProfileService.PROFILE_CACHE_PREFIX, user_id)

    def _get_cached(self, user_id):
        result = self.redis.get(self._get_key(user_id))
        if result:
            return json.loads(result)
        return None

    def get_profile(self, user_id):
        profile = self._get_cached(user_id)
        if profile:
            return profile
        profile = self.user_profile.by_user_id(user_id)
        if not profile:
            return None
        context = {
            'model': model,
            'session': model.Session,
        }
        profile = table_dictize(profile, context)

        # Put in cache
        self.redis.setex(self._get_key(user_id),
                         json.dumps(profile),
                         UserProfileService.CACHE_TIMEOUT)
        return profile

    def get_interests(self, user_id):
        profile = self.get_profile(user_id) or {}
        return profile.get('interests')

    def get_interests_boost(self, user_id):
        cached = self.redis.get(self._get_key(user_id, 'boost_params'))
        if cached:
            return json.loads(cached)


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
                'idx_keywords': interests.get('keywords', []),
                'idx_tags': interests.get('tags', []),
                'idx_research_questions': interests.get('research_questions', []),
            },
            '^0.5': {
                'idx_keywords': searches.get('keywords', []),
                'idx_tags': searches.get('tags', []),
                'idx_research_questions': searches.get('research_questions', []),
            }
        }

        self.redis.setex(self._get_key(user_id, 'boost_params'),
                         json.dumps(values),
                         UserProfileService.CACHE_TIMEOUT)

        return values
    
    def get_last_relevant(self, user_id):
        relevant = {
            'tags': set(),
            'keywords': set(),
            'research_questions': set(),
        }

        def _action(action_name, context, data_dict):
            try:
                return toolkit.get_action(action_name)(context, data_dict)
            except Exception as e:
                log.warning('Failed to execute %s. Error: %s', action_name, str(e))
            return None

        keywords = set()

        for package_id in self.user_query_result.get_last_relevant(user_id, 'dataset', 5):
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
        
        for rq in self.user_query_result.get_last_relevant(user_id, 'research_question', 5):
            relevant['research_questions'].add(rq)
        
        for dashboard in self.user_query_result.get_last_relevant(user_id, 'dashboard', 5):
            dashboard = _action('dashboard_show', {'ignore_auth': True}, {'id': dashboard})
            if dashboard and dashboard.get('tags'):
                for tag in dashboard['tags'].split(','):
                    tag = _action('tag_show', {'ignore_auth': True}, {'id': tag})
                    if tag:
                        relevant['tags'].add(tag['name'])

        for keyword in keywords:
            keyword = _action('keyword_show', {'ignore_auth': True}, {'id': keyword})
            if keyword:
                relevant['keywords'].add(keyword['name']) 

        return relevant


user_profile_service = UserProfileService()