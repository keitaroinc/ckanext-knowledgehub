import ckan.plugins.toolkit as toolkit
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

#from ckanext.knowledgehub.lib.solr import Indexed, mapped
#from ckanext.knowledgehub.model import Theme, SubThemes

from sqlalchemy import types, ForeignKey, Column, Table, or_
import datetime
import logging

log = logging.getLogger(__name__)


ml_model = Table(
    'ml_model',
    metadata,
    Column('id',
            types.UnicodeText,
           primary_key=True,
           default=make_uuid
    ),
    Column('model_name', types.UnicodeText),
    Column('model_type', types.UnicodeText),
    Column('model_version', types.UnicodeText),
    Column('data', types.LargeBinary),
    Column('created_at',
        types.DateTime,
        default=datetime.datetime.utcnow),
)

train_data = Table(
    'train_data',
    metadata,
    Column('id',
            types.UnicodeText,
           primary_key=True,
           default=make_uuid
    ),
    Column('data_type', types.UnicodeText),
    Column('name', types.UnicodeText),
    Column('description', types.UnicodeText),
    Column('data_header', types.JSON),
    Column('created_at',
        types.DateTime,
        default=datetime.datetime.utcnow),
    Column('modified_at',
           types.DateTime,
           onupdate=datetime.datetime.utcnow),
)

train_data_entries = Table(
    'train_data_entries',
    metadata,
    Column('id',
            types.UnicodeText,
           primary_key=True,
           default=make_uuid
    ),
    Column('created_at',
        types.DateTime,
        default=datetime.datetime.utcnow),
    Column('data', types.JSON)
)

train_job = Table(
    'train_job',
    metadata,
    Column('job_id', types.Text),
    Column('worker_id', types.Text),
    Column('job_status', types.Text),
    Column('started_at',
        types.DateTime,
        default=datetime.datetime.utcnow),
    Column('configuration', types.JSON)
)