import datetime
import logging

from ckan import logic
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject
from ckan.model import Tag, tag_table

from sqlalchemy import types, ForeignKey, Column, Table, or_
from sqlalchemy.orm import column_property

log = logging.getLogger(__name__)


keyword_table = Table(
    'keyword', metadata,
    Column('id',
           types.UnicodeText,
           primary_key=True,
           default=make_uuid),
    Column('created_at',
           types.DateTime,
           default=datetime.datetime.utcnow),
    Column('modified_at',
           types.DateTime,
           default=datetime.datetime.utcnow),
    Column('name', types.UnicodeText, nullable=False),
)


class Keyword(DomainObject):

    @classmethod
    def get(cls, ref):
        return Session.query(cls).get(ref)
    
    @classmethod
    def by_name(cls, name):
        query = Session.query(cls)
        query = query.filter(keyword_table.c.name == name)
        return query.first()
    
    @classmethod
    def get_tags(cls, keyword_id):
        query = Session.query(Tag)
        query = query.filter(tag_table.c.keyword_id == keyword_id)
        return query.all()
    
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

mapper(Keyword, keyword_table)

def column_exists_in_db(column_name, table_name, engine):
    for result in engine.execute('select column_name '
                                 'from information_schema.columns '
                                 'where table_name=\'%s\'' % table_name):
        column = result[0]
        if column == column_name:
            return True
    return False


def extend_tag_table():
    from ckan import model
    engine = model.meta.engine

    tag_table.append_column(Column(
        'keyword_id',
        types.UnicodeText,
    ))

    #Tag.keyword_id = property(column_property(tag_table.c.keyword_id))
    from sqlalchemy.orm import configure_mappers

    # Hack to update the mapper for the class Tag that already have been mapped
    delattr(Tag,'_sa_class_manager')
    mapper(Tag, tag_table)  # Remap the Tag class again

    if column_exists_in_db('keyword_id', 'tag', engine): 
        return
    
    # Add the column in DB
    engine.execute('alter table tag '
                   'add column keyword_id character varying(100)')



def setup():
    extend_tag_table()
    metadata.create_all(engine)
    
