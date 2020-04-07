import datetime
import json
import ast
from itertools import product
from sqlalchemy import (
    types,
    Column,
    Table,
    or_,
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


log = getLogger(__name__)

get_action = logic.get_action

__all__ = ['Dashboard', 'dashboard_table']


def ensure_column(table_name, column_name, column_type, engine):
    """Ensure that the column exists in the table. If not, add it.
    :param table_name: the table to check.
    :type table_name: string
    :param column_name: the name of the column to check for.
    :type column_name: string
    :param column_type: column type definition.
    :type column_type: string
    :param engine: configured SQLAlchemy engine.
    :type engine: sqlachemy.engine.Engine
    """

    insp = reflection.Inspector.from_engine(engine)
    has_column = False
    for col in insp.get_columns(table_name):
        if column_name.lower() == col['name'].lower():
            has_column = True
            break

    log.debug('Check if column %s is present in table %s: %s',
              column_name, table_name, 'Yes' if has_column else 'No')

    if not has_column:
        engine.execute('ALTER TABLE %(table_name)s ADD '
                       'COLUMN %(column_name)s %(column_type)s' % {
                            "table_name": table_name,
                            "column_name": column_name,
                            "column_type": column_type
                        })
        log.debug('Added column %s (type %s) to %s', column_name, column_type,
                  table_name)


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
    Column('tags', types.UnicodeText),
    Column('datasets', types.UnicodeText),
    Column('shared_with_users', types.UnicodeText),
    Column('shared_with_groups', types.UnicodeText),
    Column('shared_with_organizations', types.UnicodeText),
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
        'research_questions',
        'datasets',
        'keywords',
        mapped('tags', 'tags'),
        mapped('groups', 'groups'),
        mapped('organizations', 'organizations'),
        mapped('created_at', 'khe_created'),
        mapped('modified_at', 'khe_modified'),
        unprefixed('idx_keywords'),
        unprefixed('idx_tags'),
        unprefixed('idx_research_questions'),
        unprefixed('idx_shared_with_users'),
        unprefixed('idx_shared_with_organiztions'),
        unprefixed('idx_shared_with_groups'),
        unprefixed('idx_datasets'),
        unprefixed('permission_labels'),
        unprefixed('idx_groups'),
        unprefixed('idx_organizations'),
    ]
    doctype = 'dashboard'

    @classmethod
    def before_index(cls, data):
        indicators = []
        if data.get('indicators'):
            indicators = json.loads(data['indicators'])

        datasets = {}
        organizations = {}
        pdorganizations = {}
        groups = {}
        pdgroups = {}
        research_questions = {}
        visualizations = {}
        tags = {}
        keywords = {}

        research_question_ids = set()
        resource_view_ids = set()
        if data.get('type') == 'internal':
            for k in indicators:
                if k.get('research_question'):
                    research_question_ids.add(k['research_question'])
                if k.get('resource_view_id'):
                    resource_view_ids.add(k['resource_view_id'])
        else:
            if isinstance(indicators, unicode) or isinstance(indicators, str):
                # The indicator seems to be the research question ID
                research_question_ids.add(indicators)
            elif isinstance(indicators, list):
                for i in indicators:
                    research_question_ids.add(i['research_question'])
            else:
                log.warning('The indicators was expected to be string/unicode '
                            'or list, however %s was received. Indicators: %s',
                            str(type(indicators)),
                            str(indicators))

        # Load packages (when external dashboard)
        if data.get('datasets'):
            for dataset_id in map(lambda _id: _id.strip(),
                                  filter(lambda _id: _id and _id.strip(),
                                         data.get('datasets', '').split(','))):
                pkg = cls._get_package(dataset_id)
                if pkg:
                    datasets[pkg['id']] = pkg

        # Load the research questions related to this dashboard.
        for research_question_id in research_question_ids:
            try:
                rq = get_action('research_question_show')({
                    'ignore_auth': True,
                }, {
                    'id': research_question_id,
                })
                research_questions[rq['id']] = rq
            except Exception as e:
                log.warning('Failed to research question %s. Error: %s',
                            research_question_id,
                            str(e))
                log.exception(e)

        # Load resource views (visualizations). Also loads the packages.
        for resource_view_id in resource_view_ids:
            try:
                rv = get_action('resource_view_show')({
                    'ignore_auth': True,
                }, {
                    'id': resource_view_id,
                })
                visualizations[rv['id']] = rv
                if rv['package_id'] not in datasets:
                    pkg = cls._get_package(rv['package_id'])
                    if pkg:
                        datasets[pkg['id']] = pkg
            except Exception as e:
                log.warning('Failed to fetch resource view %s. Error: %s',
                            resource_view_id,
                            str(e))
                log.exception(e)

        # Load tags and keywords
        if data.get('tags'):
            for tag_id in map(lambda t: t.strip(),
                              filter(lambda t: t and t.strip(),
                                     data.get('tags', '').split(','))):
                try:
                    tag = get_action('tag_show')({
                        'ignore_auth': True,
                    }, {
                        'id': tag_id,
                    })
                    tags[tag['id']] = tag

                    keyword_id = tag.get('keyword_id')
                    if keyword_id and keyword_id not in keywords:
                        try:
                            keyword = get_action('keyword_show')({
                                'ignore_auth': True,
                            }, {
                                'id': keyword_id,
                            })
                            keywords[keyword['id']] = keyword
                        except Exception as e:
                            log.warning('Failed to fetch keyword %s. '
                                        'Error: %s',
                                        keyword_id,
                                        str(e))
                            log.exception(e)
                except Exception as e:
                    log.warning('Failed to fetch tag %s. Error: %s',
                                tag_id,
                                str(e))
                    log.exception(e)

        # set groups and organizations
        for _, pkg in datasets.items():
            pdorganizations[pkg['id']] = {}
            pdgroups[pkg['id']] = {}
            if pkg.get('organization'):
                org = pkg['organization']
                organizations[org['id']] = org
                pdorganizations[pkg['id']][org['id']] = org
            if pkg.get('groups'):
                for group in pkg['groups']:
                    groups[group['id']] = group
                    pdgroups[pkg['id']][org['id']] = org

            # Handle if dataset is explicitly shared with an organization or
            # group: the dataset may be treated as it belongs to that group.
            exp_shared_orgs = get_as_list('shared_with_organizations', pkg)
            exp_shared_groups = get_as_list('shared_with_groups', pkg)
            all_groups = {}
            all_groups.update(organizations)
            all_groups.update(groups)
            for exp_groups, is_org in [(exp_shared_orgs, True),
                                       (exp_shared_groups, False)]:
                for group_id in exp_groups:
                    if group_id not in all_groups:
                        group = cls._get_group(group_id, is_org)
                        if group:
                            if is_org:
                                organizations[group['id']] = group
                                pdorganizations[pkg['id']][group['id']] = group
                            else:
                                groups[group['id']] = group
                                pdgroups[pkg['id']][group['id']] = group
                    else:
                        group = all_groups[group_id]
                        if is_org:
                            pdorganizations[pkg['id']][group['id']] = group
                        else:
                            pdgroups[pkg['id']][group['id']] = group

        # Set data
        data['datasets'] = ','.join(datasets.keys())
        data['idx_datasets'] = list(datasets.keys())
        data['research_questions'] = ','.join(map(lambda (_, rq): rq['title'],
                                                  research_questions.items()))
        data['organizations'] = ','.join(map(lambda (_, o): o['name'],
                                             organizations.items()))
        data['groups'] = ','.join(map(lambda (_, g): g['name'],
                                      groups.items()))
        data['tags'] = ','.join(map(lambda (_, t): t['name'], tags.items()))
        data['keywords'] = ','.join(map(lambda (_, k): k['name'],
                                        keywords.items()))

        # Set idx_ (id index) for usage in user interests
        data['idx_research_questions'] = list(research_questions.keys())
        data['idx_tags'] = list(map(lambda (_, t): t['name'], tags.items()))
        data['idx_keywords'] = list(map(lambda (_, k): k['name'],
                                        keywords.items()))

        permission_labels = cls._generate_dashboard_permission_labels(
            data,
            datasets,
            pdorganizations,
            pdgroups,
        )
        if permission_labels:
            data['permission_labels'] = permission_labels

        data['idx_organizations'] = list(organizations.keys())
        data['idx_groups'] = list(groups.keys())

        return data

    @classmethod
    def _generate_dashboard_permission_labels(cls,
                                              data,
                                              datasets,
                                              organizations,
                                              groups):
        permission_labels = []
        users = {}
        user_ids = set()

        if data.get('created_by'):
            permission_labels.append('creator-%s' % data['created_by'])

        if data.get('shared_with_users'):
            shared_with = cls._get_safe_shared_with(data['shared_with_users'])
            for user_id in map(lambda _id: _id.strip(),
                               filter(lambda _id: _id and _id.strip(),
                                      shared_with.split(','))):
                user = cls._get_user(user_id)
                if user:
                    users[user['id']] = user
        data['shared_with_users'] = ','.join(users.keys())
        data['idx_shared_with_users'] = list(users.keys())

        # Attach permission labels for explicit sharing (with user,
        # organization or group)
        permission_labels += get_permission_labels(data)

        # We generate a permission label that defines the access (implicit)
        # to this dashboard. One dashboard can be accessed by a user that
        # can also access ALL datasets that provide data to this dashboard.
        # This is implicit access.
        # One dashboard can use data from multiple datasets, each of those
        # can be accessed by the users in multiple organizations or groups.
        # For example a dashboard can have data from datasets D1 and D2, each
        # of which can be accessed by the users of:
        # D1(orgA, orgB, groupC) and D2(orgD, groupE)
        # So a user can view this dashboard if he belongs to any of the: orgA,
        # orgB or groupC AND at the same time belongs to orgD or groupE.
        # To encode this, we generate a permission label like so:
        # member-groups-orgA|orgB|groupC+orgD|groupE
        # once the prefix 'member-groups-' is removed, we are left with the
        # sets of groups separated with '+'. The user must belong to all of
        # these sets. To belong to a set it means to be part of ANY of the
        # group or organization in that set. The group/org ids are separeted
        # with '|' in the set.
        any_groups = []
        for pkgid, _ in datasets.items():
            pgroups = groups.get(pkgid, {}).keys()
            porgs = organizations.get(pkgid, {}).keys()
            if pgroups + porgs:
                any_groups.append(pgroups + porgs)
        if any_groups:
            combined_label = '+'.join(['|'.join(_ids) for _ids in any_groups])
            permission_labels.append('match-groups-{}'.format(combined_label))

        # Check each dataset, if explicitly shared with users.
        # If there are users that have access to all datasets, then we must
        # add the same permission label for those users (user-<id>) the
        # dashboard as well to add access to those users to this dataset.
        shared_users = []
        for _, dataset in datasets.items():
            user_with_access = set()
            if dataset.get('shared_with_users'):
                shared_with = cls._get_safe_shared_with(
                    dataset['shared_with_users'])
                for user_id in map(lambda u: u.strip(),
                                   filter(lambda u: u and u.strip(),
                                          shared_with.split(','))):
                    # We might get the ID or the name of the user
                    user = cls._get_user(user_id)
                    if user:
                        user_with_access.add(user['id'])

            shared_users.append(user_with_access)

        if shared_users:
            if len(datasets) == 1:
                for user_id in shared_users[0]:
                    permission_labels.append('user-%s' % user_id)
            else:
                user_with_access = shared_users[0]
                for i in range(1, len(shared_users)):
                    user_with_access = \
                        user_with_access.intersection(shared_users[i])

                for user_id in user_with_access:
                    permission_labels.append('user-%s' % user_id)

        return permission_labels

    @classmethod
    def _get_safe_shared_with(cls, value):
        '''This function returns a comma separated string of the values in
        properties like shared_with_users.
        Because earlier version kept these properties differently - some were
        serializing a set (string value {"a","b","c"}), and some are keeping
        json versions of the values, this function will check for those cases
        and will return a comma separated string of the values always.
        '''
        if isinstance(value, list):
            return ','.join(value)
        if value.startswith('{') and value.endswith('}'):
            return value[1:-1]
        if value.startswith('"') and value.endswith('"'):
            return ','.join(json.loads('[%s]' % value))
        return value

    @classmethod
    def _get_user(cls, user_id):
        try:
            return get_action('user_show')({
                'ignore_auth': True,
            }, {
                'id': user_id,
            })
        except Exception as e:
            log.warning('Failed to fetch user %s. Error: %s', user_id, str(e))
            log.exception(e)
        return None

    @classmethod
    def _get_package(cls, pkg_id):
        try:
            pkg = get_action('package_show')({
                'ignore_auth': True,
            }, {
                'id': pkg_id,
            })
            return pkg
        except Exception as e:
            log.warning('Failed to get package %s. Error: %s',
                        dataset_id,
                        str(e))
            log.exception(e)
        return None

    @classmethod
    def _get_group(cls, group_id, is_org):
        action = 'organization_show' if is_org else 'group_show'
        try:
            return get_action(action)({
                'ignore_auth': True,
            }, {
                'id': group_id
            })
        except Exception as e:
            log.warning('Failed to execute %s for id %s. Error: %s',
                        action, group_id, str(e))
            log.exception(e)
        return None

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


def dashboard_table_upgrade(_engine=None):
    if _engine is None:
        from ckan.model.meta import engine as ckan_model_engine
        _engine = ckan_model_engine
    log.debug('Upgrading table ckanext_knowledgehub_dashboard...')
    for column_name in ['shared_with_organizations', 'shared_with_groups']:
        ensure_column('ckanext_knowledgehub_dashboard',
                      column_name,
                      'text',
                      _engine)
        log.debug('Ensured column %s is present.', column_name)
    log.info('Table ckanext_knowledgehub_dashboard upgraded successfully.')


mapper(Dashboard, dashboard_table)


def setup():
    metadata.create_all(engine)
    dashboard_table_upgrade(engine)
