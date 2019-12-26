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

user_query = Table(
    'user_query',
    metadata,
    Column('id',
            types.UnicodeText,
           primary_key=True,
           default=make_uuid
    ),
    Column(
        'query_text',
        types.UnicodeText
    ),
    Column('created_at',
           types.DateTime,
           default=datetime.datetime.utcnow),
    Column('user_id',
           types.UnicodeText),
    Column('query_type',
           types.UnicodeText)
)


user_query_result = Table(
    'user_query_result',
    metadata,
    Column('id',
            types.UnicodeText,
           primary_key=True,
           default=make_uuid
    ),
    Column('query_id', types.UnicodeText),
    Column('user_id', types.UnicodeText),
    Column('created_at',
           types.DateTime,
           default=datetime.datetime.utcnow),
    Column('result_type', types.UnicodeText), # dataset, visualization, research_question etc
    Column('result_id', types.UnicodeText),   # ID of the dataset/visualization/rq etc
)


class UserQuery(DomainObject):

    @classmethod
    def get(cls, reference):
        pass

    @classmethod
    def add_query(cls, query):
        pass

    @classmethod
    def get_all(cls, page, size):
        pass


class UserQueryResult(DomainObject):

    @classmethod
    def get(cls, reference):
        pass

    @classmethod
    def add_query_result(cls, result):
        pass

    @classmethod
    def search(cls, **kwargs):
        pass

mapper(UserQuery, user_query)
mapper(UserQueryResult, user_query_result)


def setup():
    metadata.create_all(user_query)
    metadata.create_all(user_query_result)