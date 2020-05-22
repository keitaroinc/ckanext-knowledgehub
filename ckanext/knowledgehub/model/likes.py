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
    def get_likes_count(cls, ref):
        likes_count = Session.query(cls).get(ref)
        if likes_count:
            return likes_count.count
        return 0


mapper(LikesRef, likes_ref_table)
mapper(LikesCount, likes_count_table)


def setup():
    metadata.create_all(engine)
