import datetime

import ckan.logic as logic
from ckan import model
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, desc

__all__ = [
    'SubThemes',
    'sub_themes_table',
    'setup'
]

sub_themes_table = None


class SubThemes(DomainObject):

    @classmethod
    def get(cls, **kwargs):
        limit = kwargs.get('limit')
        offset = kwargs.get('offset')
        order_by = kwargs.get('order_by')

        kwargs.pop('limit', None)
        kwargs.pop('offset', None)
        kwargs.pop('order_by', None)

        query = Session.query(cls).autoflush(False)
        query = query.filter_by(**kwargs)

        if order_by:
            column = order_by.split(' ')[0]
            order = order_by.split(' ')[1]
            query.order_by("%s %s" % (column, order))

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        return query

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


sub_themes_table = Table(
    'sub_themes',
    metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('name', types.UnicodeText, nullable=False, unique=True),
    Column('description', types.UnicodeText),
    Column('theme_id', types.UnicodeText, nullable=False),
    Column('created_at', types.DateTime, default=datetime.datetime.now),
    Column('modified_at', types.DateTime, onupdate=datetime.datetime.now),
    Column('created_by', types.UnicodeText, nullable=False),
    Column('modified_by', types.UnicodeText),
)

mapper(
    SubThemes,
    sub_themes_table,
)


def setup():
    metadata.create_all(model.meta.engine)