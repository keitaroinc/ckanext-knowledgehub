from ckan import model
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, desc


class AnalyticalFramework(DomainObject):

    @classmethod
    def get_all(cls, limit=5):
        obj = Session.query(cls).autoflush(False)
        return obj.limit(limit).all()


analytical_framework_table = Table(
    'analytical_framework',
    metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('theme', types.UnicodeText),
    Column('sub_theme', types.UnicodeText),
    Column('research_question', types.UnicodeText),
    Column('schema', types.UnicodeText),
    Column('indicators', types.UnicodeText),
)

mapper(
    AnalyticalFramework,
    analytical_framework_table,
)

def af_db_setup():
    metadata.create_all(model.meta.engine)

