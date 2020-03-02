import ckan.plugins.toolkit as toolkit
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.logic import get_action
from ckan.model.domain_object import DomainObject

from ckanext.knowledgehub.lib.solr import Indexed, mapped
from ckanext.knowledgehub.model import Theme, SubThemes

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
           types.UnicodeText),
    Column('sub_theme',
           types.UnicodeText),
    Column('image_url',
           types.UnicodeText),
    Column('title',
           types.UnicodeText),
    Column('author',
           types.UnicodeText),
    Column('tags',
           types.UnicodeText),
    Column('created_at',
           types.DateTime,
           default=datetime.datetime.utcnow),
    Column('modified_at',
           types.DateTime,
           onupdate=datetime.datetime.utcnow),
    Column('modified_by',
           types.UnicodeText),
    Column('state',
           types.UnicodeText,
           default=u'active'),
)


class ResearchQuestion(DomainObject, Indexed):

    doctype = 'research_question'
    indexed = [
        mapped('id', 'entity_id'),
        'name',
        'title',
        'author',
        'theme_id',
        'theme_name',
        'theme_title',
        'sub_theme_id',
        'sub_theme_name',
        'sub_theme_title',
        'image_url',
        'tags',
        'keywords',
        mapped('tags', 'tags'),
        mapped('created_at', 'khe_created'),
        mapped('modified_at', 'khe_modified'),
    ]

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

    @staticmethod
    def before_index(data):
        if data.get('theme'):
            theme = Theme.get(data['theme'])
            data['theme_id'] = theme.id
            data['theme_name'] = theme.name
            data['theme_title'] = theme.title
        if data.get('sub_theme'):
            sub_theme = SubThemes.get(data['sub_theme']).first()
            data['sub_theme_id'] = sub_theme.id
            data['sub_theme_name'] = sub_theme.name
            data['sub_theme_title'] = sub_theme.title

        keywords = set()
        if data.get('tags'):
            data['tags'] = data.get('tags').split(',')
            data['idx_tags'] = data['tags']
            for tag in data['tags']:
                tag_obj = get_action('tag_show')(
                    {'ignore_auth': True},
                    {'id': tag}
                )
                da['idx_tags'].append(tag)
                if tag_obj.get('keyword_id'):
                    keyword_obj = get_action('keyword_show')(
                        {'ignore_auth': True},
                        {'id': tag_obj.get('keyword_id')}
                    )
                    keywords.add(keyword_obj.get('name'))
                    if keywords:
                        data['keywords'] = ','.join(keywords)

        if keywords:
            data['keywords'] = ','.join(keywords)
            data['idx_keywords'] = list(keywords)

        return data

    def __repr__(self):
        return '<ResearchQuestion %s>' % self.title


mapper(
    ResearchQuestion,
    research_question
)


def setup():
    metadata.create_all(engine)
