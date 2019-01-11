# encoding: utf-8
import datetime

from sqlalchemy import (
    types,
    Column,
    Table,
)

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
    Column('name', types.UnicodeText),
    Column('title', types.UnicodeText),
    Column('description', types.UnicodeText),
    Column('created', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('modified', types.DateTime,
           default=datetime.datetime.utcnow),
    )


class Theme(DomainObject):

    @classmethod
    def get(self, **kwds):
        '''
        Finds a single entity in the table.
        '''
        query = Session.query(self).autoflush(False)
        query = query.filter_by(**kwds).first()
        return query

    @classmethod
    def delete(cls, id):
        '''
        Delete single entry in the table.
        '''
        obj = Session.query(cls).filter_by(id=id).first()
        if not obj:
            raise logic.NotFound

        Session.delete(obj)
        Session.commit()


mapper(Theme, theme_table)


def theme_table_setup():
    metadata.create_all(engine)
