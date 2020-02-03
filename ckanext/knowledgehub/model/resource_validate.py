import datetime

import ckan.logic as logic
from ckan import model
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, desc, asc, or_

__all__ = [
    'ResourceValidate',
    'resource_validate_table',
    'setup'
]

resource_validate_table = Table(
    'resource_validate',
    metadata,
    Column(
        'id',
        types.UnicodeText,
        primary_key=True,
        default=make_uuid),
    Column(
        'what',
        types.UnicodeText,
        nullable=False),
    Column(
        'resource',
        types.UnicodeText,
        ForeignKey('resource.id', ondelete='CASCADE'),
        nullable=False),
    Column(
        'who',
        types.UnicodeText,
        nullable=False),
    Column(
        'when',
        types.DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow)
)


class ResourceValidate(DomainObject):

    @classmethod
    def get(cls, **kwargs):
        if not len(kwargs):
            return None
        query = Session.query(cls).autoflush(False)
        query = query.filter_by(**kwargs)

        return query.first()

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


mapper(
    ResourceValidate,
    resource_validate_table,
)


def setup():
    metadata.create_all(model.meta.engine)
