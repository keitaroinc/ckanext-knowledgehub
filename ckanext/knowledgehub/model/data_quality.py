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
        return (Session.query(cls)
                       .filter_by(type=_type, ref_id=ref_id)
                       .order_by(data_quality_metrics_table.c.modified_at.desc())
                       .first())

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
