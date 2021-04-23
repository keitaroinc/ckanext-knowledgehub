# encoding: utf-8

"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

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
