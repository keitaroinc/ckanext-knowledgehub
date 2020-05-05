import datetime
import json
import ast
from itertools import product
from sqlalchemy import (
    types,
    Column,
    Table,
    or_,
    ForeignKey,
    func,
)
from sqlalchemy.engine import reflection

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
from ckanext.knowledgehub.lib.solr import (
    Indexed,
    mapped,
    unprefixed,
)
from ckanext.knowledgehub.logic.auth import get_permission_labels
from ckanext.knowledgehub.lib.util import get_as_list
from logging import getLogger
from ckan.model import (
    User,
    user_table,
)


access_request_table = Table(
    'access_request',
    metadata,
    Column('id', types.UnicodeText,
           primary_key=True, default=make_uuid),
    Column('user_id', types.UnicodeText, nullable=False),
    Column('created_at', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('modified_at', types.DateTime,
           default=datetime.datetime.utcnow),
    Column('entity_type', types.String(20), nullable=False),
    Column('entity_ref', types.UnicodeText, nullable=False),
    Column('status', types.String(20), nullable=False, default='pending'),
    Column('resolved_by', types.UnicodeText),
)

assigned_access_requests_table = Table(
    'assigned_access_requests',
    metadata,
    Column('request_id',
           types.UnicodeText,
           ForeignKey('access_request.id'),
           primary_key=True),
    Column('user_id', types.UnicodeText, primary_key=True),
)


class AccessRequest(DomainObject):

    @classmethod
    def get(cls, ref):
        return Session.query(cls).get(ref)

    @classmethod
    def get_active_for_user_and_entity(cls, entity_type, entity_ref, user_id):
        q = Session.query(cls)
        q = q.filter(access_request_table.c.entity_type == entity_type)
        q = q.filter(access_request_table.c.entity_ref == entity_ref)
        q = q.filter(access_request_table.c.user_id == user_id)
        q = q.filter(access_request_table.c.status == 'pending')
        print q
        return q.first()

    @classmethod
    def get_all(cls,
                assigned_to=None,
                requested_by=None,
                order_by='created_at desc',
                status='pending',
                offset=0,
                limit=20):
        q = Session.query(AccessRequest, User).join(AssignedAccessRequest)
        q = q.join(User, user_table.c.id == access_request_table.c.user_id)
        if assigned_to:
            q = q.filter(
                assigned_access_requests_table.c.user_id == assigned_to)
        if requested_by:
            q = q.filter(access_request_table.c.user_id == requested_by)
        if status:
            q = q.filter(access_request_table.c.status == status)

        q = q.order_by(order_by)
        q = q.limit(limit).offset(offset)

        return q.all()

    @classmethod
    def get_all_count(cls,
                      assigned_to=None,
                      requested_by=None,
                      order_by='created_at desc',
                      status='pending'):
        q = Session.query(func.count(func.distinct(access_request_table.c.id)))
        if assigned_to:
            q = q.join(AssignedAccessRequest)
            q = q.filter(
                assigned_access_requests_table.c.user_id == assigned_to)
        if requested_by:
            q = q.filter(access_request_table.c.user_id == requested_by)
        if status:
            q = q.filter(access_request_table.c.status == status)

        return q.scalar()


class AssignedAccessRequest(DomainObject):

    @classmethod
    def get_assigned_request(cls, request_id, user_id):
        q = Session.query(cls)
        q = q.filter(assigned_access_requests_table.c.user_id == user_id)
        q = q.filter(assigned_access_requests_table.c.request_id == request_id)

        return q.first()

    @classmethod
    def delete_assigned_requests(cls, request_id):
        pass


mapper(AccessRequest, access_request_table)
mapper(AssignedAccessRequest, assigned_access_requests_table)


def setup():
    metadata.create_all(engine)
