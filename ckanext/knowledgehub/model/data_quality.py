import datetime

import ckan.logic as logic
from ckan import model
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject
import ckan.lib.dictization as d

from sqlalchemy import types, ForeignKey, Column, Table, desc, asc, or_


data_quality_metrics_table = Table(
    'data_quality_metrics',
    metadata,
    Column('id', types.UnicodeText,
           primary_key=True, default=make_uuid),
    Column('created_at', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('modified_at', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('type', types.UnicodeText, nullable=False),
    Column('ref_id', types.UnicodeText, nullable=False),
    Column('resource_last_modified', types.DateTime),
    Column('completeness', types.Float),
    Column('uniqueness', types.Float),
    Column('timeliness', types.String),
    Column('validity', types.Float),
    Column('accuracy', types.Float),
    Column('consistency', types.Float),
    Column('metrics', types.JSON),
)


class DataQualityMetrics(DomainObject):

    @classmethod
    def get(cls, _type, ref_id):
        return Session.query(cls).filter_by(type=_type, ref_id=ref_id).first()

    @classmethod
    def get_dataset_metrics(cls, ref_id):
        return cls.get('package', ref_id)

    @classmethod
    def get_resource_metrics(cls, ref_id):
        return cls.get('resource', ref_id)

    @classmethod
    def update(cls, filter, metrics):
        obj = Session.query(cls).filter_by(**filter)
        if isinstance(metrics, DataQualityMetrics):
            metrics = d.table_dictize(metrics, {'model': cls})
        obj.update(metrics)
        Session.commit()

        return obj.first()

    @classmethod
    def remove(cls, _type, ref_id):
        pass


mapper(DataQualityMetrics, data_quality_metrics_table)


def setup():
    metadata.create_all(engine)
