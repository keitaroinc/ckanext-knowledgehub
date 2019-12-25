from ckan.plugins import toolkit
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

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
           default=make_uuid),
    Column('query_text',
           types.UnicodeText),
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
           default=make_uuid),
    Column('query_id', types.UnicodeText),
    Column('user_id', types.UnicodeText),
    Column('created_at',
           types.DateTime,
           default=datetime.datetime.utcnow),
    # dataset, visualization, research_question etc
    Column('result_type', types.UnicodeText),
    # ID of the dataset/visualization/rq etc
    Column('result_id', types.UnicodeText),
)


class UserQuery(DomainObject):

    @classmethod
    def get(cls, reference):
        '''Returns a user_query object referenced by its id.'''
        if not reference:
            return None

        return Session.query(cls).get(reference)

    @classmethod
    def add_query(cls, query):
        pass

    @classmethod
    def get_all(cls, page=None, limit=None, order_by='created_at desc'):
        offset = None
        if page and limit:
            offset = (page - 1) * limit

        query = Session.query(cls).autoflush(False)

        if order_by:
            query = query.order_by(order_by)

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        return query.all()


class UserQueryResult(DomainObject):

    @classmethod
    def get(cls, reference):
        '''Returns a user_query_result object referenced by its id.'''
        if not reference:
            return None

        return Session.query(cls).get(reference)

    @classmethod
    def add_query_result(cls, result):
        pass

    @classmethod
    def search(cls, **kwargs):
        q = kwargs.get('q')
        limit = kwargs.get('limit')
        offset = kwargs.get('offset')
        order_by = kwargs.get('order_by')

        kwargs.pop('q', None)
        kwargs.pop('limit', None)
        kwargs.pop('offset', None)
        kwargs.pop('order_by', None)

        query = Session.query(cls).autoflush(False)
        query = query.filter_by(**kwargs)

        if q:
            query = query.filter(
                or_(cls.result_type.contains(q),
                    cls.result_type.ilike(r"%{}%".format(q)))
            )

        if order_by:
            query = query.order_by(order_by)

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        return query


mapper(UserQuery, user_query)
mapper(UserQueryResult, user_query_result)


def setup():
    metadata.create_all(user_query)
    metadata.create_all(user_query_result)
