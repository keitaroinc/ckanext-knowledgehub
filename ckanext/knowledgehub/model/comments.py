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


comments_table = Table(
    'comments',
    metadata,
    Column('id', types.UnicodeText,
           primary_key=True, default=make_uuid),
    Column('created_at', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('modified_at', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('created_by', types.String(128), nullable=False, index=True),
    Column('ref', types.String(128), nullable=False, index=True),
    Column('content', types.UnicodeText, default='', nullable=False),
    Column('thread_id', types.String(128), nullable=True, index=True),
    Column('reply_to', types.String(128), nullable=True, index=True),
    Column('deleted', types.Boolean, nullable=False, default=True),
    Column('replies_count', types.Integer, nullable=False, default=0),
)


comments_refs_stats_table = Table(
    'comments_refs_stats',
    metadata,
    Column('ref', types.UnicodeText, primary_key=True),
    Column('comment_count', types.Integer, nullable=False, default=0)
)


class Comment(DomainObject):

    @classmethod
    def get(cls, comment_id):
        return Session.query(cls).get(comment_id)

    @classmethod
    def get_comments(cls, ref, offset=0, limit=20, max_replies=3):
        comments = OrderedDict()

        q = Session.query(cls).filter(
            comments_table.c.ref == ref
        ).filter(
            comments_table.c.thread_id.is_(None)
        ).order_by(
            comments_table.c.created_at.desc()
        ).offset(offset).limit(limit)

        for comment in q.all():
            comments[comment.id] = {
                'comment': comment,
                'replies': [],
            }

        if comments:
            sub = Session.query(cls, func.rank().over(
                order_by=comments_table.c.created_at.desc(),
                partition_by=comments_table.c.thread_id,
            ).label('rank')).filter(
                comments_table.c.thread_id.in_(comments.keys())
            ).filter(
                comments_table.c.thread_id == comments_table.c.reply_to
            ).filter(
                comments_table.c.ref == ref
            ).subquery()

            q = Session.query(cls).select_entity_from(sub).filter(
                sub.c.rank <= max_replies
            )
            q = q.offset(offset).limit(limit)

            for reply in q.all():
                replies = comments[reply.thread_id]['replies']
                replies.append(reply)

        return [comment for _, comment in comments.iteritems()]

    @classmethod
    def get_comments_count(cls, ref):
        q = Session.query(comments_refs_stats_table.c.comment_count).filter(
            comments_refs_stats_table.c.ref == ref
        )
        return q.scalar()

    @classmethod
    def get_thread(cls, ref, thread_id):
        q = Session.query(cls).filter(
            comments_table.c.ref == ref
        ).filter(
            comments_table.c.thread_id == thread_id
        ).order_by(
            comments_table.c.created_at.desc()
        )

        return q.all()

    @classmethod
    def increment_reply_count(cls, ref, comment_id):
        Session.query().filter(
            comments_table.c.comment_id == comment_id,
        ).update({
            'reply_count': (comments_table.c.reply_count + 1)
        })

        Session.query.filter(
            comments_refs_stats_table.c.ref == ref,
        ).update({
            'comment_count': (comments_refs_stats_table.c.comment_count + 1),
        })

    @classmethod
    def decrement_reply_count(cls, ref, comment_id):
        Session.query().filter(
            comments_table.c.comment_id == comment_id,
        ).update({
            'reply_count': (comments_table.c.reply_count - 1)
        })

        Session.query.filter(
            comments_refs_stats_table.c.ref == ref,
        ).update({
            'comment_count': (comments_refs_stats_table.c.comment_count - 1),
        })


mapper(Comment, comments_table)


def setup():
    metadata.create_all(engine)
