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
    def get_notifications(cls, user_id, limit=0, offset=10, before=None):
        query = Session.query(cls).filter(
            notification_table.c.recepient == user_id,
            notification_table.c.seen != True
        )
        if before is not None:
            query = query.filter(
                notification_table.c.created_at < before
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
        return query.count()

    @classmethod
    def mark_read(cls, user_id, notifications=None):
        statement = update(cls)

        if notifications:
            statement = statement.where(
                notification_table.c.recepient == user_id)
            statement = statement.where(
                notification_table.c.id.in_(notifications))
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
