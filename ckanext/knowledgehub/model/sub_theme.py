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
    def get(cls, limit=10):
        obj = Session.query(cls).autoflush(False)
        return obj.limit(limit).all()

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