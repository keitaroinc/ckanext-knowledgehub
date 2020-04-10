from ckan.plugins import toolkit
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from ckanext.knowledgehub.lib.solr import (
    Indexed,
    mapped,
    unprefixed,
)

from sqlalchemy import types, ForeignKey, Column, Table, or_, update
from sqlalchemy.sql.expression import func
import datetime
import logging


log = logging.getLogger(__name__)


__all__ = ['Posts', 'posts_table']


posts_table = Table(
    'posts',
    metadata,
    Column('id',
           types.String(lenght=256),
           primary_key=True,
           default=make_uuid),
    Column('created_at',
           types.DateTime,
           default=datetime.datetime.utcnow),
    Column('created_by', types.String(lenght=256))
    Column('title', types.UnicodeText, nullable=False),
    Column('description', types.UnicodeText),
    Column('entity_type', types.String(lenght=256)),
    Column('entity_ref', types.String(lenght=256)),
    Column('comment_count', types.Number, default=0),
    Column('like_count', types.Number, default=0),
)


class Posts(DomainObject, Indexed):

    doctype = 'post'
    indexed = [
        mapped('id', 'entity_id'),
        'title',
        'description',
        'created_at',
        'created_by',
        'entity_type',
        'entity_ref',
        'comment_count',
        'like_count',
    ]

    @classmethod
    def get(cls, ref):
        q = Session.query(cls).find(ref)
        return q.first()
    

mapper(Posts, posts_table)


def setup():
    metadata.create_all(engine)
