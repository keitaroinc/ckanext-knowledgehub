import ckan.plugins.toolkit as toolkit
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table
import datetime
import logging

log = logging.getLogger(__name__)


__all__ = [
    'ResearchQuestion', 'research_question_table',
]

research_question_table = None


def setup():
    if research_question_table is None:
        define_research_question_table()
        log.debug('research_question table defined in memory')

        if not research_question_table.exists():
            research_question_table.create()
    else:
        log.debug('research_question table already exist')


class ResearchQuestion(DomainObject):

    @classmethod
    def get(cls, id, default=None):
        kwds = {'id': id}
        o = Session.query(cls).autoflush(False)
        o = o.filter_by(**kwds).first()
        if o:
            return o
        else:
            return default

    @classmethod
    def search(cls, text_query):
        text_query = text_query.strip().lower()
        q = Session.query(cls).filter(cls.content.ilike(r"%{}%".format(text_query)))
        q = q.filter(cls.state == 'active')
        q = q.order_by(cls.content)
        return q.all()

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
    global research_question_table
    research_question_table = Table('research_question', metadata,
                                    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
                                    Column('theme', types.UnicodeText, ForeignKey('theme.id')),
                                    Column('sub_theme', types.UnicodeText, ForeignKey('sub_theme.id')),
                                    Column('content', types.UnicodeText),
                                    Column('author', types.UnicodeText, ForeignKey('user.id')),
                                    Column('created', types.DateTime, default=datetime.datetime.now),
                                    Column('modified', types.DateTime),
                                    Column('state', types.UnicodeText, default=u'active'),
                                    )

    mapper(
        ResearchQuestion,
        research_question_table
    )
