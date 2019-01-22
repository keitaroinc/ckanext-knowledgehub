# encoding: utf-8
import datetime

from sqlalchemy import (
    types,
    Column,
    Table,
    or_,
)

from ckan.common import _

from ckan.model.meta import (
    metadata,
    mapper,
    Session,
    engine
    )
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject
import ckan.logic as logic


__all__ = ['Theme', 'theme_table']


theme_table = Table(
    'theme', metadata,
    Column('id', types.UnicodeText,
           primary_key=True, default=make_uuid),
    Column('name', types.UnicodeText,
           nullable=False, unique=True),
    Column('title', types.UnicodeText),
    Column('description', types.UnicodeText),
    Column('created', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('modified', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('state', types.UnicodeText,
           default=u'active'),
    Column('author', types.UnicodeText),
    Column('author_email', types.UnicodeText),
    )


class Theme(DomainObject):

    @classmethod
    def get(cls, reference):
        '''Returns a theme object referenced by its id or name.'''
        if not reference:
            return None

        theme = Session.query(cls).get(reference)
        if theme is None:
            theme = cls.by_name(reference)
        return theme

    @classmethod
    def search(cls, **kwargs):
        limit = kwargs.get('limit')
        offset = kwargs.get('offset')
        order_by = kwargs.get('order_by')
        q = kwargs.get('q')

        kwargs.pop('limit', None)
        kwargs.pop('offset', None)
        kwargs.pop('order_by', None)
        kwargs.pop('q', None)

        if q:
            query = Session.query(cls) \
                .filter(or_(cls.name.contains(q),
                            cls.title.ilike('%' + q + '%')))
        else:
            query = Session.query(cls) \
                .filter_by(**kwargs)

        if order_by:
            column = order_by.split(' ')[0]
            order = order_by.split(' ')[1]
            query = query.order_by("%s %s" % (column, order))

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
            raise logic.NotFound(_(u'Theme'))


mapper(Theme, theme_table)


def theme_db_setup():
    metadata.create_all(engine)
