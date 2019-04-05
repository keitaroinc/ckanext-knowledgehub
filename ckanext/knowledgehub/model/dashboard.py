import datetime

from sqlalchemy import (
    types,
    Column,
    Table,
)

from ckan.model.meta import (
    metadata,
    mapper,
    engine
)
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

__all__ = ['Dashboard', 'dashboard_table']

dashboard_table = Table(
    'ckanext_knowledgehub_dashboard', metadata,
    Column('id', types.UnicodeText,
           primary_key=True, default=make_uuid),
    Column('name', types.UnicodeText,
           nullable=False, unique=True),
    Column('title', types.UnicodeText, nullable=False),
    Column('description', types.UnicodeText, nullable=False),
    Column('type', types.UnicodeText, nullable=False),
    Column('source', types.UnicodeText),
    Column('indicators', types.JSON),
    Column('created_at', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('modified_at', types.DateTime,
           default=datetime.datetime.utcnow),
)


class Dashboard(DomainObject):
    # TODO(Aleksandar): Implement actions
    pass


mapper(Dashboard, dashboard_table)


def setup():
    metadata.create_all(engine)
