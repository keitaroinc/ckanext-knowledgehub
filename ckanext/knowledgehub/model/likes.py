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
import json
from itertools import product
from collections import OrderedDict
from sqlalchemy import (
    types,
    Column,
    Table,
    or_,
    ForeignKey,
    func,
)
from ckan.model.meta import (
    metadata,
    mapper,
    engine,
    Session
)
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject
from logging import getLogger


log = getLogger(__name__)


likes_ref_table = Table(
    'likes_ref',
    metadata,
    Column('ref', types.UnicodeText, primary_key=True),
    Column('user_id', types.UnicodeText, primary_key=True),
)


likes_count_table = Table(
    'likes_count',
    metadata,
    Column('ref', types.UnicodeText, primary_key=True),
    Column('count', types.Integer, nullable=False, default=0),
)


class LikesRef(DomainObject):

    @classmethod
    def get(cls, user_id, ref):
        return Session.query(cls).filter(
            likes_ref_table.c.user_id == user_id
        ).filter(
            likes_ref_table.c.ref == ref
        ).first()

    @classmethod
    def get_user_liked_refs(cls, user_id, refs):
        q = Session.query(cls).filter(
            likes_ref_table.c.user_id == user_id
        ).filter(
            likes_ref_table.c.ref.in_(refs)
        )

        liked_refs = set()
        for like in q.all():
            liked_refs.add(like.ref)

        return liked_refs


class LikesCount(DomainObject):

    @classmethod
    def get(cls, ref):
        return Session.query(cls).get(ref)

    @classmethod
    def get_likes_count(cls, ref):
        likes_count = Session.query(cls).get(ref)
        if likes_count:
            return likes_count.count
        return 0

    @classmethod
    def get_likes_count_all(cls, refs):
        counts = {}
        for count in Session.query(cls).filter(
            likes_count_table.c.ref.in_(refs)
        ).all():
            counts[count.ref] = count.count
        return counts


mapper(LikesRef, likes_ref_table)
mapper(LikesCount, likes_count_table)


def setup():
    metadata.create_all(engine)
