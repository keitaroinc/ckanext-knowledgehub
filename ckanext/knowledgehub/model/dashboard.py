import datetime
import json
import ast
from sqlalchemy import (
    types,
    Column,
    Table,
    or_,
)

from ckan.model.meta import (
    metadata,
    mapper,
    engine,
    Session
)
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject
from ckan.logic import get_action
import ckan.logic as logic
from ckan.common import _
from ckanext.knowledgehub.lib.solr import Indexed, mapped

__all__ = ['Dashboard', 'dashboard_table']

dashboard_table = Table(
    'ckanext_knowledgehub_dashboard', metadata,
    Column('id', types.UnicodeText,
           primary_key=True, default=make_uuid),
    Column('name', types.UnicodeText,
           nullable=False, unique=True),
    Column('title', types.UnicodeText, nullable=False),
    Column('description', types.UnicodeText, nullable=False),
    Column('type', types.UnicodeText, nullable=False),
    Column('source', types.UnicodeText),
    Column('indicators', types.UnicodeText),
    Column('created_at', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('modified_at', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('created_by', types.UnicodeText, nullable=False),
)


class Dashboard(DomainObject, Indexed):

    indexed = [
        mapped('id', 'entity_id'),
        'name',
        'title',
        'description',
        'type',
        'source',
        'indicators',
        'research_questions'
    ]
    doctype = 'dashboard'


    @staticmethod
    def before_index(data):    
        ind = []
        if data.get('indicators'):
            ind = json.loads(data['indicators'])
        list_rqs = []
        data['research_questions'] = []
        for k in ind:
            res_q = get_action('research_question_show')({'ignore_auth': True},
            {'id': k['research_question']})
            list_rqs.append(res_q['title'])
        data['research_questions'] = ','.join(list_rqs)    
        return data

    @classmethod
    def get(cls, reference):
        '''Returns a dashboard object referenced by its id or name.'''
        if not reference:
            return None

        dashboard = Session.query(cls).get(reference)
        if dashboard is None:
            dashboard = cls.by_name(reference)

        return dashboard

    @classmethod
    def delete(cls, filter):
        obj = Session.query(cls).filter_by(**filter).first()
        if obj:
            Session.delete(obj)
            Session.commit()
        else:
            raise logic.NotFound(_(u'Dashboard'))

    @classmethod
    def search(cls, **kwargs):
        limit = kwargs.get('limit')
        offset = kwargs.get('offset')
        order_by = kwargs.get('order_by')
        q = kwargs.get('q')

        kwargs.pop('limit', None)
        kwargs.pop('offset', None)
        kwargs.pop('order_by', None)
        kwargs.pop('q', None)

        if q:
            query = Session.query(cls) \
                .filter(or_(cls.name.contains(q),
                            cls.title.ilike('%' + q + '%'),
                            cls.description.ilike('%' + q + '%')))
        else:
            query = Session.query(cls) \
                .filter_by(**kwargs)

        if order_by:
            column = order_by.split(' ')[0]
            order = order_by.split(' ')[1]
            query = query.order_by("%s %s" % (column, order))

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        return query


mapper(Dashboard, dashboard_table)


def setup():
    metadata.create_all(engine)
