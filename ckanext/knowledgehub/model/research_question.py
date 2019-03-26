import ckan.plugins.toolkit as toolkit
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, or_
import datetime
import logging

log = logging.getLogger(__name__)


__all__ = [
    'ResearchQuestion', 'research_question',
]


research_question = Table(
    'research_question',
    metadata,
    Column('id',
           types.UnicodeText,
           primary_key=True,
           default=make_uuid),
    Column('name', types.UnicodeText,
           nullable=False,
           unique=True),
    Column('theme',
           types.UnicodeText,
           ForeignKey('theme.id')),
    Column('sub_theme',
           types.UnicodeText,
           ForeignKey('sub_themes.id')),
    Column('image_url',
           types.UnicodeText),
    Column('title',
           types.UnicodeText),
    Column('author',
           types.UnicodeText),
    Column('created_at',
           types.DateTime,
           default=datetime.datetime.now),
    Column('modified_at',
           types.DateTime,
           onupdate=datetime.datetime.now),
    Column('modified_by',
           types.UnicodeText),
    Column('state',
           types.UnicodeText,
           default=u'active'),
    )


class ResearchQuestion(DomainObject):

    @classmethod
    def get(cls, id_or_name=None, **kwargs):
        q = kwargs.get('q')
        limit = kwargs.get('limit')
        offset = kwargs.get('offset')
        order_by = kwargs.get('order_by')

        kwargs.pop('q', None)
        kwargs.pop('limit', None)
        kwargs.pop('offset', None)
        kwargs.pop('order_by', None)

        query = Session.query(cls).autoflush(False)
        query = query.filter_by(**kwargs)

        if id_or_name:
            query = query.filter(
                or_(cls.id == id_or_name,
                    cls.name == id_or_name)
            )

        if q:
            query = query.filter(
                cls.title.ilike(r"%{}%".format(q)))

        if order_by:
            query = query.order_by(order_by)

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        return query

    @classmethod
    def update(cls, filter, data):
        obj = Session.query(cls).filter_by(**filter)
        obj.update(data)
        Session.commit()

        return obj.first()

    @classmethod
    def all(cls, theme=None, sub_theme=None,
            state=('active',)):
        # TODO Handle filtering by sub/theme properly
        q = Session.query(cls)
        if state:
            q = q.filter(cls.state.in_(state))

        return q.order_by(cls.title)

    @classmethod
    def delete(cls, id):
        kwds = {'id': id}
        obj = Session.query(cls).\
            filter_by(**kwds).first()
        if not obj:
            raise toolkit.ObjectNotFound
        Session.delete(obj)
        Session.commit()

    def __repr__(self):
        return '<ResearchQuestion %s>' % self.title


mapper(
    ResearchQuestion,
    research_question
)


def setup():
    metadata.create_all(engine)
