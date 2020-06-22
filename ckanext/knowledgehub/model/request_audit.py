from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.logic import get_action
from ckan.model.domain_object import DomainObject


from sqlalchemy import types, ForeignKey, Column, Table, or_, func
import datetime
import logging


log = logging.getLogger(__name__)


request_audit_table = Table(
    'request_audit',
    metadata,
    Column('id',
           types.Integer,
           primary_key=True,
           autoincrement=True),
    Column('remote_ip',
           types.String(128),
           nullable=True,
           index=True),
    Column('remote_user',
           types.String(128),
           nullable=True,
           index=True),
    Column('session',
           types.String(128),
           nullable=True,
           index=True),
    Column('current_language',
           types.String(128),
           nullable=True),
    Column('access_time',
           types.DateTime,
           nullable=True,
           index=True),
    Column('request_url',
           types.UnicodeText,
           nullable=True),
    Column('http_method',
           types.String(128),
           nullable=True),
    Column('http_path',
           types.UnicodeText,
           nullable=True),
    Column('http_query_params',
           types.UnicodeText,
           nullable=True),
    Column('http_user_agent',
           types.UnicodeText,
           nullable=True),
    Column('client_os',
           types.UnicodeText,
           nullable=True),
    Column('client_device',  # Browser from user-agent string
           types.UnicodeText,
           nullable=True),
)


class RequestAudit(DomainObject):

    @classmethod
    def get(cls, reference):
        return Session.query(cls).get(reference)

    @classmethod
    def insert_bulk(cls, records):
        Session.bulk_save_objects(records)
        Session.commit()

    @classmethod
    def get_all(cls,
                query=None,
                start_time=None,
                end_time=None,
                offset=0,
                limit=20):
        q = Session.query(cls)

        if query:
            q = q.filter(
                or_(
                    request_audit_table.c.request_url.like('%{}%'.format(
                        query)),
                    request_audit_table.c.remote_user.like('%{}%'.format(
                        query)),
                    request_audit_table.c.remote_ip.like('%{}%'.format(query)),
                )
            )

        if start_time and end_time:
            q = q.filter(
                request_audit_table.c.access_time.between(start_time, end_time)
            )
        elif start_time:
            q = q.filter(
                request_audit_table.c.access_time >= start_time
            )
        elif end_time:
            q = q.filter(
                request_audit_table.c.access_time <= end_time
            )

        q = q.order_by(
            request_audit_table.c.access_time.desc(),
        )
        count = q.count()

        q = q.offset(offset).limit(limit)

        return count, q.all()

    @classmethod
    def _get_report_by(cls,
                       column,
                       query,
                       start_time,
                       end_time,
                       offset,
                       limit):
        if start_time or end_time or query:
            return cls._get_report_by_filter(column, query, start_time,
                                             end_time, offset, limit)
        return cls._get_report_by_nofilter(column, offset, limit)

    @classmethod
    def _get_report_by_nofilter(cls, column, offset, limit):
        count = func.count(request_audit_table.c.id).label('cnt')
        q = Session.query(
            column,
            count,
        )

        q = q.group_by(
            column,
        )

        q = q.order_by(
            count.desc()
        )

        items_count = q.count()

        q = q.offset(offset).limit(limit)

        return items_count, q.all()

    @classmethod
    def _get_report_by_filter(cls,
                              column,
                              query,
                              start_time,
                              end_time,
                              offset,
                              limit):
        sq = Session.query(request_audit_table.c.id, column.label('value'))

        if query:
            sq = sq.filter(
                or_(
                    request_audit_table.c.request_url.like('%{}%'.format(
                        query)),
                    request_audit_table.c.remote_user.like('%{}%'.format(
                        query)),
                    request_audit_table.c.remote_ip.like('%{}%'.format(query)),
                )
            )

        if start_time and end_time:
            sq = sq.filter(
                request_audit_table.c.access_time.between(start_time, end_time)
            )
        elif start_time:
            sq = sq.filter(
                request_audit_table.c.access_time >= start_time
            )
        elif end_time:
            sq = sq.filter(
                request_audit_table.c.access_time <= end_time
            )

        sq = sq.subquery('sq')

        count = func.count(sq.c.id)

        q = Session.query(sq.c.value, count)
        q = q.group_by(sq.c.value)
        q = q.order_by(
            count.desc()
        )

        items_count = q.count()

        q = q.offset(offset).limit(limit)

        return items_count, q.all()

    @classmethod
    def get_report_by(cls,
                      report=None,
                      query=None,
                      start_time=None,
                      end_time=None,
                      offset=0,
                      limit=20):
        columns = {
            'endpoint': request_audit_table.c.http_path,
            'remote_user': request_audit_table.c.remote_user,
            'remote_ip': request_audit_table.c.remote_ip,
        }

        if report not in columns:
            raise Exception('Invalid column for report: %s' % report)

        column = columns[report]

        return cls._get_report_by(column, query, start_time,
                                  end_time, offset, limit)


mapper(RequestAudit, request_audit_table)


def setup():
    metadata.create_all(engine)
