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


user_profile_table = Table(
    'user_profile', metadata,
    Column('id', types.UnicodeText,
           primary_key=True, default=make_uuid),
    Column('user_id', types.UnicodeText,
            nullable=False, unique=True),
    Column('interests', types.JSON),
    Column('user_notified', types.Boolean,
            default=False)
)


class UserProfile(DomainObject):

    @classmethod
    def by_user_id(cls, user_id):
        query = Session.query(cls)
        query = query.filter(user_profile_table.c.user_id == user_id)
        return query.first()

    @classmethod
    def get_list(cls, page=1, limit=20, order_by=None):
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


mapper(UserProfile, user_profile_table)


def setup():
    metadata.create_all(engine)
