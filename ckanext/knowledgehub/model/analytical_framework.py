import datetime

from ckan import model
from ckan.common import _
import ckan.logic as logic
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, desc


class AnalyticalFramework(DomainObject):

    @classmethod
    def get(cls, **kwargs):
        limit = kwargs.get('limit')
        offset = kwargs.get('offset')
        order_by = kwargs.get('order_by')

        kwargs.pop('limit', None)
        kwargs.pop('offset', None)
        kwargs.pop('order_by', None)

        query = Session.query(cls).autoflush(False)
        query = query.filter_by(**kwargs)

        if order_by:
            column = order_by.split(' ')[0]
            order = order_by.split(' ')[1]

            query.order_by("%s %s" % (column, order))

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        return query.all()

    @classmethod
    def delete(cls, id):
        query = {'id': id}
        obj = Session.query(cls).filter_by(**query).first()
        if obj:
            Session.delete(obj)
            Session.commit()
        else:
            raise logic.NotFound



analytical_framework_table = Table(
    'analytical_framework',
    metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('theme', types.UnicodeText),
    Column('sub_theme', types.UnicodeText),
    Column('research_question', types.UnicodeText),
    Column('schema', types.UnicodeText),
    Column('indicators', types.UnicodeText),
    Column('createdAt', types.DateTime, default=datetime.datetime.now),
    Column('modifiedAt', types.DateTime)
)

mapper(
    AnalyticalFramework,
    analytical_framework_table,
)

def af_db_setup():
    metadata.create_all(model.meta.engine)
