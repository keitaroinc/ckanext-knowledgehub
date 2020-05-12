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
    Column('entity_title', types.UnicodeText),
    Column('entity_link', types.UnicodeText),
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
        '''Looks up an access request by its ID.

        :param ref: `str`, the access request ID.

        :returns: `AccessRequest` object or `None`.
        '''
        return Session.query(cls).get(ref)

    @classmethod
    def get_active_for_user_and_entity(cls, entity_type, entity_ref, user_id):
        '''Looks up an active (status `pending`) access request that has not
        been granted or declined yet.

        :param entity_type: `str`, the entity type.
        :param entity_ref: `str`, the entity ID (reference).
        :param user_id: `str`, the id of the user that requested access.

        :returns: `AccessRequest` object or `None`.
        '''
        q = Session.query(cls)
        q = q.filter(access_request_table.c.entity_type == entity_type)
        q = q.filter(access_request_table.c.entity_ref == entity_ref)
        q = q.filter(access_request_table.c.user_id == user_id)
        q = q.filter(access_request_table.c.status == 'pending')
        return q.first()

    @classmethod
    def get_all(cls,
                assigned_to=None,
                requested_by=None,
                order_by='created_at desc',
                status='pending',
                search='',
                offset=0,
                limit=20):
        '''Queries for access requests assigned to a user. Additional filtering
        is also possible.

        :param assigned_to: `str`, the ID of the user that the access requests
            are assigned to.
        :param requested_by: `str`, the ID of the user that requested the
            access.
        :param order_by: `str`, order by clause.
        :param status: `str`, access request status. Default is `pending`.
        :param search: `str`, search string to be matched against the entity
            title.
        :param offset: `int`, pagination offset.
        :param limit: `int`, pagination limit.

        :returns: iterable of matching `AccessRequest` objects.
        '''
        q = Session.query(AccessRequest, User).join(AssignedAccessRequest)
        q = q.join(User, user_table.c.id == access_request_table.c.user_id)
        if assigned_to:
            q = q.filter(
                assigned_access_requests_table.c.user_id == assigned_to)
        if requested_by:
            q = q.filter(access_request_table.c.user_id == requested_by)
        if status:
            q = q.filter(access_request_table.c.status == status)
        if search:
            q = q.filter(func.lower(access_request_table.c.entity_title).like(
                func.lower('%{}%'.format(search))))

        q = q.order_by(order_by)
        q = q.limit(limit).offset(offset)

        return q.all()

    @classmethod
    def get_all_count(cls,
                      assigned_to=None,
                      requested_by=None,
                      order_by='created_at desc',
                      status='pending',
                      search=''):
        '''Counts the total number of matching access requests based on the
        provided criteria.

        :param assigned_to: `str`, the ID of the user that the access requests
            are assigned to.
        :param requested_by: `str`, the ID of the user that requested the
            access.
        :param order_by: `str`, order by clause.
        :param status: `str`, access request status. Default is `pending`.
        :param search: `str`, search string to be matched against the entity
            title.

        :returns: `int`, total number of matching records.
        '''
        q = Session.query(func.count(func.distinct(access_request_table.c.id)))
        if assigned_to:
            q = q.join(AssignedAccessRequest)
            q = q.filter(
                assigned_access_requests_table.c.user_id == assigned_to)
        if requested_by:
            q = q.filter(access_request_table.c.user_id == requested_by)
        if status:
            q = q.filter(access_request_table.c.status == status)

        if search:
            q = q.filter(func.lower(access_request_table.c.entity_title).like(
                func.lower('%{}%'.format(search))))

        return q.scalar()


class AssignedAccessRequest(DomainObject):

    @classmethod
    def get_assigned_request(cls, request_id, user_id):
        '''Looks up if there is an assigned access request for the given user
        and the given request id.

        :param request_id: `str`, the access request ID.
        :param user_id: `str`, the ID of the user that the request is assigned
            to.

        :returns: `AssignedAccessRequest` object or `None`.
        '''
        q = Session.query(cls)
        q = q.filter(assigned_access_requests_table.c.user_id == user_id)
        q = q.filter(assigned_access_requests_table.c.request_id == request_id)

        return q.first()

    @classmethod
    def delete_assigned_requests(cls, request_id):
        '''Deletes all assigned records for a particular request.

        :param request_id: `str`, the ID of the request for which to delete the
            assigned records.
        '''
        d = assigned_access_requests_table.delete().where(
            assigned_access_requests_table.c.request_id == request_id
        )
        d.execute()


mapper(AccessRequest, access_request_table)
mapper(AssignedAccessRequest, assigned_access_requests_table)


def setup():
    metadata.create_all(engine)
