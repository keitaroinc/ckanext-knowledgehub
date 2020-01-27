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
    Column('data_package_id', types.UnicodeText),
    Column('created_at',
        types.DateTime,
        default=datetime.datetime.utcnow),
    Column('data', types.JSON)
)

train_job = Table(
    'train_job',
    metadata,
    Column('job_id',
           types.Text,
           primary_key=True,
           default=make_uuid),
    Column('worker_id', types.Text),
    Column('job_status', types.Text),
    Column('started_at',
        types.DateTime,
        default=datetime.datetime.utcnow),
    Column('configuration', types.JSON)
)


class MLModel(DomainObject):

    @classmethod
    def get(cls, referece):
        pass

    @classmethod
    def get_by_version(cls, model_name, version):
        pass
    
    @classmethod
    def get_latest(cls, model_name):
        pass

    @classmethod
    def create_model(cls, model):
        pass

    @classmethod
    def remove_model(cls, reference):
        pass


class TrainData(DomainObject):

    @classmethod
    def get(cls, referece):
        pass

    @classmethod
    def get_by_name(cls, data_set_name):
        pass

    @classmethod
    def create_data(cls, data):
        pass

    @classmethod
    def update(cls, data):
        pass

    @classmethod
    def remove(cls, reference):
        pass

    @classmethod
    def add_entry(cls, data_package, data_entry):
        pass

    @classmethod
    def add_entries(cls, data_package, entries):
        pass


class TrainDataEntries(DomainObject):
    pass

class TrainJob(DomainObject):

    @classmethod
    def get(cls, reference):
        pass

    @classmethod
    def get_all(cls, page, size):
        pass

    @classmethod
    def get_all_with_status(cls, status, page, size):
        pass

    @classmethod
    def create_job(cls, job):
        pass

    @classmethod
    def get_jobs_for_worker(cls, worker_id):
        pass

    @classmethod
    def update_job(cls, job):
        pass

    @classmethod
    def remove_job(cls, job_id):
        pass


mapper(MLModel, ml_model)
mapper(TrainData, train_data)
mapper(TrainDataEntries, train_data_entries)
mapper(TrainJob, train_job)


def setup():
    metadata.create_all(engine)

