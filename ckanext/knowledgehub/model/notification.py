from ckan.plugins import toolkit
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, or_, update
from sqlalchemy.sql.expression import func
import datetime
import logging

log = logging.getLogger(__name__)


notification_table = Table(
    'notification',
    metadata,
    Column('id',
           types.UnicodeText,
           primary_key=True,
           default=make_uuid),
    Column('created_at',
           types.DateTime,
           default=datetime.datetime.utcnow),
    Column('recepient', types.UnicodeText),
    Column('title', types.UnicodeText, nullable=False),
    Column('description', types.UnicodeText),
    Column('link', types.Text),
    Column('image', types.Text),
    Column('seen', types.Boolean, default=False),
)


class Notification(DomainObject):

    @classmethod
    def get(cls, reference):
        return Session.query(cls).get(reference)

    @classmethod
    def get_notifications(cls, user_id, limit=0, offset=10):
        query = Session.query(cls).filter(
            notification_table.c.recepient == user_id,
            notification_table.c.seen != True
        )
        query = query.order_by(notification_table.c.created_at.desc())

        query = query.offset(offset).limit(limit)

        return query.all()
    
    @classmethod
    def get_notifications_count(cls, user_id):
        query = Session.query(cls).filter(
            notification_table.c.recepient == user_id,
            notification_table.c.seen != True
        )
        return  query.count()

    @classmethod
    def mark_read(cls, user_id, notifications=None):
        statement = update(cls)
        
        if notifications:
            statement = statement.where(
                notification_table.c.recepient == user_id and \
                notification_table.c.id.in_(notifications)
            )
        else:
            statement = statement.where(
                notification_table.c.recepient == user_id
            )

        statement = statement.values({'seen': True})

        Session.execute(statement)
        Session.commit()


mapper(Notification, notification_table)


def setup():
    metadata.create_all(engine)