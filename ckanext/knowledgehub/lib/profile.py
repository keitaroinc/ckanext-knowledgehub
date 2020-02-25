'''User interests service.
'''
import json
from ckan.lib.redis import connect_to_redis
import ckan.model as model
from ckan.lib.dictization import table_dictize

from ckanext.knowledgehub.model import UserProfile



class UserProfileService:

    PROFILE_CACHE_PREFIX = 'ckanext.knowledgehub.user.profile'
    CACHE_TIMEOUT = 5*60  # 5 minutes

    def __init__(self, redis=None, user_profile=UserProfile):
        self.redis = redis or connect_to_redis()
        self.user_profile = user_profile
    

    def _get_key(self, user_id):
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
        interests = self.get_interests(user_id)

        if not interests:
            return None

        values = {
            'idx_keywords': interests.get('keywords', []),
            'idx_tags': interests.get('tags', []),
            'idx_research_questions': interests.get('research_questions', []),
        }

        return values


user_profile_service = UserProfileService()