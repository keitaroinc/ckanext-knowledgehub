import ckan.plugins.toolkit as toolkit
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

#from ckanext.knowledgehub.lib.solr import Indexed, mapped
#from ckanext.knowledgehub.model import Theme, SubThemes

from sqlalchemy import types, ForeignKey, Column, Table, or_
import datetime
import logging

log = logging.getLogger(__name__)

user_intents = Table(
    'user_intents',
    metadata,
    Column('id',
            types.UnicodeText,
           primary_key=True,
           default=make_uuid
    ),
    Column('created_at',
           types.DateTime,
           default=datetime.datetime.utcnow),
    Column('user_id', types.UnicodeText),
    Column('user_query_id', types.UnicodeText),
    Column('primary_category', types.UnicodeText),
    Column('theme', types.UnicodeText),
    Column('sub_theme', types.UnicodeText),
    Column('research_question', types.UnicodeText),
    Column('inferred_transactional', types.UnicodeText),
    Column('inferred_navigational', types.UnicodeText),
    Column('inferred_informational', types.UnicodeText),
    Column('curated', types.Boolean),
    Column('accurate', types.Boolean)
)

class UserIntents(DomainObject):
    
    @classmethod
    def get(cls, reference):
       pass

    @classmethod
    def add_user_intent(self, user_intent):
        pass

    @classmethod
    def get_list(cls, page, offset):
        pass
    
    @classmethod
    def update(cls, user_intent):
        pass

mapper(UserIntents, user_intents)

def setup():
    metadata.create_all(engine)
              