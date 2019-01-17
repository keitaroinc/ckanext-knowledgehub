import ckan.plugins.toolkit as toolkit
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table
import datetime
import logging

log = logging.getLogger(__name__)


__all__ = [
    'ResearchQuestion', 'research_question',
]

research_question = None


def setup():
    if research_question is None:
        define_research_question_table()
        log.debug('research_question table defined in memory')

        if not research_question.exists():
            research_question.create()
    else:
        log.debug('research_question table already exist')


class ResearchQuestion(DomainObject):

    @classmethod
    def get(cls, **kwargs):
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

        if q:
            query = query.filter(cls.content.ilike(r"%{}%".format(q)))

        if order_by:
            column = order_by.split(' ')[0]
            order = order_by.split(' ')[1]
            query = query.order_by("%s %s" % (column, order))

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        return query

    @classmethod
    def all(cls, theme=None, sub_theme=None, state=('active',)):
        # TODO Handle filtering by sub/theme properly
        q = Session.query(cls)
        if state:
            q = q.filter(cls.state.in_(state))

        return q.order_by(cls.content)

    @classmethod
    def delete(cls, id):
        kwds = {'id': id}
        obj = Session.query(cls).filter_by(**kwds).first()
        if not obj:
            raise toolkit.ObjectNotFound
        Session.delete(obj)
        Session.commit()

    def __repr__(self):
        return '<ResearchQuestion %s>' % self.content


def define_research_question_table():
    global research_question
    research_question = Table('research_question', metadata,
                                    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
                                    Column('theme', types.UnicodeText, ForeignKey('theme.id')),
                                    Column('sub_theme', types.UnicodeText, ForeignKey('sub_themes.id')),
                                    Column('content', types.UnicodeText),
                                    Column('author', types.UnicodeText, ForeignKey('user.id')),
                                    Column('created', types.DateTime, default=datetime.datetime.now),
                                    Column('modified', types.DateTime),
                                    Column('state', types.UnicodeText, default=u'active'),
                                    )

    mapper(
        ResearchQuestion,
        research_question
    )
