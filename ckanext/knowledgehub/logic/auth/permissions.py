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

u'''Helper function to manage permission labels for multiple indexed entities.
'''

from ckan import model
from ckan.model.meta import Session


_PERMISSION_LABEL_PREFIX = {
    'shared_with_users': 'user-%s',
    'shared_with_organizations': 'member-%s',
    'shared_with_groups': 'member-%s',
}


def get_permission_labels(data_dict):
    permission_labels = data_dict.get('permission_labels', [])

    for field, prefix_template in _PERMISSION_LABEL_PREFIX.items():
        if data_dict.get(field):
            ids = [s.strip() for s in data_dict[field].strip().split(',')]
            for id in ids:
                if id:
                    label = prefix_template % id
                    if label not in permission_labels:
                        permission_labels.append(label)

    return permission_labels


def get_user_permission_labels(context):
    labels = ['public']

    if context.get('auth_user_obj') is not None:
        user = context['auth_user_obj']
        labels.append('user-%s' % user.id)
        labels.append('creator-%s' % user.id)

        organizations, groups = _get_all_orgs_or_groups_for_user(user.id)

        for ids in [organizations, groups]:
            if ids:
                if len(ids) > 1:
                    labels.append('member-%s' % '-'.join(sorted(ids)))
                for _id in ids:
                    labels.append('member-%s' % _id)

    return labels


def _get_all_orgs_or_groups_for_user(user_id):
    q = Session.query(model.Member, model.Group)
    q = q.join(model.Group,
               model.member_table.c.group_id == model.group_table.c.id)
    q = q.filter(model.member_table.c.table_id == user_id)
    q = q.filter(model.member_table.c.table_name == 'user')
    q = q.filter(model.member_table.c.state == 'active')

    organizations, groups = [], []

    for _, group in q.all():
        if group.is_organization:
            organizations.append(group.id)
        else:
            groups.append(group.id)

    return (sorted(organizations), sorted(groups))
