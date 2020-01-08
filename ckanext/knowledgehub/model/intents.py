import datetime
import logging

from ckan import logic
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, or_

log = logging.getLogger(__name__)

user_intents = Table(
    'user_intents',
    metadata,
    Column('id',
           types.UnicodeText,
           primary_key=True,
           default=make_uuid),
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
        '''Returns a intent object referenced by its id.'''
        if not reference:
            return None

        return Session.query(cls).get(reference)

    @classmethod
    def add_user_intent(self, user_intent):
        Session.add(user_intent)
        Session.commit()

    @classmethod
    def get_list(cls, page=None, limit=None, order_by='created_at desc'):
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

    @classmethod
    def get_latest(cls):
        result = Session.query(cls).order_by(
            user_intents.c.created_at.desc()).limit(1).all()
        for latest_intent in result:
            return latest_intent
        return None

    @classmethod
    def update(cls, filter, data):
        obj = Session.query(cls).filter_by(**filter)
        obj.update(data)
        Session.commit()

        return obj.first()

    @classmethod
    def delete(cls, filter):
        obj = Session.query(cls).filter_by(**filter).first()
        if obj:
            Session.delete(obj)
            Session.commit()
        else:
            raise logic.NotFound

    @classmethod
    def delete_all(cls):
        Session.query(cls).delete()
        Session.commit()


mapper(UserIntents, user_intents)


def setup():
    metadata.create_all(engine)
