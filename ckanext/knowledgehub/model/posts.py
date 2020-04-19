from ckan.plugins import toolkit
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from ckanext.knowledgehub.lib.solr import (
    Indexed,
    mapped,
    unprefixed,
)

from sqlalchemy import types, ForeignKey, Column, Table, or_, update
from sqlalchemy.sql.expression import func
import datetime
import json
import logging


log = logging.getLogger(__name__)


__all__ = ['Posts', 'posts_table']


posts_table = Table(
    'posts',
    metadata,
    Column('id',
           types.String(length=256),
           primary_key=True,
           default=make_uuid),
    Column('created_at',
           types.DateTime,
           default=datetime.datetime.utcnow),
    Column('created_by', types.String(length=256)),
    Column('title', types.UnicodeText, nullable=False),
    Column('description', types.UnicodeText),
    Column('entity_type', types.String(length=256)),
    Column('entity_ref', types.String(length=256)),
    Column('comment_count', types.Integer, default=0),
    Column('like_count', types.Integer, default=0),
)


class Posts(DomainObject, Indexed):

    doctype = 'post'
    indexed = [
        mapped('id', 'entity_id'),
        'title',
        'description',
        'created_at',
        'created_by',
        'entity_type',
        'entity_ref',
        'comment_count',
        'like_count',
        unprefixed('idx_keywords'),
        unprefixed('idx_tags'),
        unprefixed('idx_research_questions'),
    ]

    @classmethod
    def get(cls, ref):
        return Session.query(cls).get(ref)

    @classmethod
    def before_index(cls, data):
        if 'entity_type' not in data:
            return data
        related_data_ids = {
            'idx_tags': [],
            'idx_keywords': [],
            'idx_research_questions': [],
        }

        related_data_loaders = {
            'dataset': cls.load_related_data_dataset,
            'dashboard': cls.load_related_data_dashboard,
            'research_question': cls.load_related_data_research_question,
            'visualization': cls.load_related_data_visualization,
        }

        if data['entity_type'] not in related_data_loaders:
            log.error('Cannot load data for related entity of type %s.',
                      data['entity_type'])
            return data

        try:
            log.info('Indexing related entity %s with ref %s',
                     data['entity_type'], data['entity_ref'])
            related_data_loaders[data['entity_type']](
                data['entity_ref'],
                related_data_ids,
            )
        except Exception as e:
            log.error('Failed to load related data '
                      'for %s (with id=%s). Error: %s',
                      data['entity_type'], data['entity_ref'], str(e))
            log.exception(e)

        data.update(related_data_ids)

        return data

    @classmethod
    def _call_action(cls, action, data):
        try:
            return toolkit.get_action(action)({
                'ignore_auth': True,
            }, data)
        except Exception as e:
            log.error('Failed while calling action %s. Args: %s. Error: %s',
                      action, str(data), str(e))
            log.exception(e)
        return None

    @classmethod
    def _try_clean_list(cls, data, prop):
        value = data.get(prop)
        if value is None:
            return []
        if isinstance(value, set):
            return list(value)
        if isinstance(value, str) or isinstance(value, unicode):
            return list(filter(None,
                               map(lambda v: v.strip(), value.split(','))))

        raise Exception('Cannot extract list from %s (type=%s)',
                        str(value), type(value))

    @classmethod
    def _load_tags_and_keywords(cls, tag_ids, related_data_ids):
        for tag in tag_ids:
            tag = cls._call_action('tag_show', {'id': tag})
            if not tag:
                continue
            if tag['id'] not in related_data_ids['idx_tags']:
                related_data_ids['idx_tags'].append(tag['id'])
            if tag.get('keyword_id') and \
                    tag['keyword_id'] not in related_data_ids:
                related_data_ids['idx_keywords'].append(tag['keyword_id'])

    @classmethod
    def load_related_data_dataset(cls, _id, related_data_ids):
        dataset = cls._call_action('package_show', {'id': _id})
        if not dataset:
            return
        for tag in dataset.get('tags', []):
            if tag['id'] not in related_data_ids['idx_tags']:
                related_data_ids['idx_tags'].append(tag['id'])
            tag = cls._call_action('tag_show', {'id': tag['id']})
            if tag and tag.get('keyword_id') and \
                    tag['keyword_id'] not in related_data_ids['idx_keywords']:
                related_data_ids['idx_keywords'].append(tag['keyword_id'])

    @classmethod
    def load_related_data_research_question(cls, _id, related_data_ids):
        if _id not in related_data_ids['idx_research_questions']:
            related_data_ids['idx_research_questions'].append(_id)
        rq = cls._call_action('research_question_show', {'id': _id})
        if not rq:
            return

        tags = cls._try_clean_list(rq, 'tags')
        cls._load_tags_and_keywords(tags, related_data_ids)

    @classmethod
    def load_related_data_visualization(cls, _id, related_data_ids):
        resource_view = cls._call_action('resource_view_show', {'id': _id})
        if not resource_view:
            return
        extras = resource_view.get('__extras', {})

        for rq_title in extras.get('research_questions', []):
            rq = cls._call_action('search_research_questions', {
                'text': rq_title,
            })
            if rq and rq.get('count', 0) > 0:
                rq = rq['results'][0]
                cls.load_related_data_research_question(rq['id'],
                                                        related_data_ids)

        tags = cls._try_clean_list(extras, 'tags')
        cls._load_tags_and_keywords(tags, related_data_ids)

    @classmethod
    def load_related_data_dashboard(cls, _id, related_data_ids):
        dashboard = cls._call_action('dashboard_show', {'id': _id})

        tags = cls._try_clean_list(dashboard, 'tags')
        cls._load_tags_and_keywords(tags, related_data_ids)

        indicators = dashboard.get('indicators', '').strip()
        if indicators:
            indicators = json.loads(indicators)
            for indicator in indicators:
                if indicator.get('research_question'):
                    cls.load_related_data_research_question(
                        indicator['research_question'],
                        related_data_ids
                    )
                if indicator.get('resource_view_id'):
                    cls.load_related_data_visualization(
                        indicator['resource_view_id'],
                        related_data_ids,
                    )
        datasets = cls._try_clean_list(dashboard, 'datasets')
        for dataset in datasets:
            dataset = dataset.strip()
            if not dataset:
                continue
            cls.load_related_data_dataset(dataset, related_data_ids)


mapper(Posts, posts_table)


def setup():
    metadata.create_all(engine)
