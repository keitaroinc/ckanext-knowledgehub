from ckan.plugins import toolkit
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, or_
from sqlalchemy.sql.expression import func
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
    Column('result_type', types.UnicodeText),
    Column('result_id', types.UnicodeText),
)


class UserQuery(DomainObject):

    @classmethod
    def get(cls, **kwargs):
        '''Returns a filtered user_query object '''
        if not len(kwargs):
            return None

        query = Session.query(cls).autoflush(False)
        query = query.order_by('created_at desc')
        query = query.filter_by(**kwargs)

        return query.first()

    @classmethod
    def add_query(cls, query):
        pass

    @classmethod
    def get_all_after(cls, after, page, size):
        page = page if page >= 1 else 1
        size = size if size >= 1 and size < 500 else 500
        query = Session.query(cls).filter(user_query.c.created_at > after)
        query.order_by(user_query.c.created_at)
        query.offset((page-1)*size).limit(size)

        results = []
        for result in query.all():
            results.append(result)
        return results

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
        page = kwargs.get('page')
        limit = kwargs.get('limit')
        order_by = kwargs.get('order_by')

        offset = None
        if page and limit:
            offset = (page - 1) * limit

        kwargs.pop('q', None)
        kwargs.pop('page', None)
        kwargs.pop('limit', None)
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

        return query.all()
    
    @classmethod
    def get_last_relevant(cls, user_id, result_type, limit=5):
        query = Session.query(
            user_query_result.c.result_id
        )
        query = query.filter(
            user_query_result.c.user_id == user_id,
            user_query_result.c.result_type == result_type)
        query = query.group_by(user_query_result.c.result_id)
        query = query.order_by(user_query_result.c.result_id.desc())
        results = query.limit(limit).all()

        return [r[0] for r in results]


mapper(UserQuery, user_query)
mapper(UserQueryResult, user_query_result)


def setup():
    metadata.create_all(engine)
