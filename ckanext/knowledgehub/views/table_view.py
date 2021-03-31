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

import logging
import json
from operator import itemgetter

from flask import Blueprint
from flask.views import MethodView
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request
from ckan.lib.navl import dictization_functions

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

render = base.render
abort = base.abort

log = logging.getLogger(__name__)


table_view = Blueprint(
    u'table_view',
    __name__,
    url_prefix=u'/dataset/<id>/resource/<resource_id>'
)


def _process_post_data(data, resource_id):

    config = {}
    filters = []
    for k, v in data.items():
        if k.startswith('data_filter_name_'):
            filter = {}
            filter_id = k.split('_')[-1]
            filter['order'] = int(filter_id)
            filter['name'] = \
                data.pop('data_filter_name_{}'.format(filter_id))
            filter['value'] = \
                data.pop('data_filter_value_{}'.format(filter_id))
            filters.append(filter)

        config['main_value'] = \
            data['table_main_value']
        config['title'] = \
            data['table_field_title']
        config['table_subtitle'] = \
            data['table_field_subtitle']
        config['table_description'] = \
            data['table_field_description']
        config['data_format'] = \
            data['table_data_format']
        config['y_axis'] = \
            data['table_field_y_axis_column']
        config['category_name'] = \
            data['table_category_name']
        config['sql_string'] = \
            data['sql_string']
        config['resource_name'] = \
            data['resource_name']
        if data.get('table_research_questions'):
            config['research_questions'] = \
                data['table_research_questions']
        if data.get('tags'):
            config['tags'] = \
                data['tags']
        else:
            config['tags'] = None

    config['filters'] = json.dumps(filters)

    view_dict = {}
    view_dict['resource_id'] = resource_id
    view_dict['title'] = config['title']
    view_dict['view_type'] = 'table'
    view_dict['tags'] = config['tags']
    view_dict.update(config)
    return view_dict


@table_view.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user,
                       auth_user_obj=g.userobj)
        check_access(u'sysadmin', context)
    except NotAuthorized:
        base.abort(403, _(u'Need to be system '
                          u'administrator to administer'))


class CreateView(MethodView):
    u''' Create new Table view '''

    def _prepare(self):

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        try:
            pass
            # check_access(u'create_indicator_view', context)
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized'
                                     u' to create a visualizations'))
        return context

    def get(self, id, resource_id, data=None, errors=None,
            error_summary=None):

        context = self._prepare()

        try:
            package = get_action('package_show')(context, {'id': id})
        except (NotFound, NotAuthorized):
            abort(404, _('Dataset not found'))

        try:
            resource = get_action('resource_show')(
                context, {'id': resource_id})
        except (NotFound, NotAuthorized):
            abort(404, _('Resource not found'))

        errors = {}
        error_summary = {}

        vars = {
            'default_sql_string':
                'SELECT * FROM "{table}"'.format(table=resource_id),
            'data': data,
            'errors': errors,
            'error_summary': error_summary,
            'pkg': package,
            'res': resource
        }
        return base.render(
            u'view/table/new_table_view_base.html',
            extra_vars=vars
        )

    def post(self, id, resource_id, data=None, errors=None,
             error_summary=None):

        context = self._prepare()

        try:
            data = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.form))))
        except dictization_functions.DataError:
            base.abort(400, _(u'Integrity Error'))

        view_dict = _process_post_data(data, resource_id)

        tags = view_dict.get('tags', '')
        if tags:
            for tag in tags.split(','):
                try:
                    check_access('tag_show', context)
                    tag_obj = get_action('tag_show')(context, {'id': tag})
                except NotFound:
                    check_access('tag_create', context)
                    tag_obj = get_action('tag_create')(context, {
                        'name': tag,
                    })

        try:
            resource_view = \
                get_action('resource_view_create')(context, view_dict)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to edit resource'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, resource_id, view_dict, errors, error_summary)

        return h.redirect_to(controller='package',
                             action='resource_views',
                             id=id, resource_id=resource_id)


class EditView(MethodView):
    u''' Edit existing Table view '''

    def _prepare(self):

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        try:
            pass
            # check_access(u'edit_indicator_view', context)
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized'
                                     u' to edit a visualizations'))
        return context

    def get(self, id, resource_id, view_id, data=None, errors=None,
            error_summary=None):

        context = self._prepare()

        # update resource should tell us early if the user has privilages.
        try:
            check_access('resource_update', context, {'id': resource_id})
        except NotAuthorized as e:
            abort(403, _('User %r not authorized to edit %s') % (g.user, id))

        # get resource and package data
        try:
            package = get_action('package_show')(context, {'id': id})
        except (NotFound, NotAuthorized):
            abort(404, _('Dataset not found'))

        try:
            resource = get_action('resource_show')(
                context, {'id': resource_id})
        except (NotFound, NotAuthorized):
            abort(404, _('Resource not found'))

        try:
            old_data = get_action('resource_view_show')(context,
                                                        {'id': view_id})
            data = data or old_data
        except (NotFound, NotAuthorized):
            abort(404, _('View not found'))

        vars = {
            'pkg': package,
            'res': resource,
            'data': data,
            'errors': errors,
            'error_summary': error_summary
        }

        return base.render(
            u'view/table/edit_table_view_base.html',
            extra_vars=vars
        )

    def post(self, id, resource_id, view_id, data=None, errors=None,
             error_summary=None):

        context = self._prepare()

        try:
            data = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.form))))
        except dictization_functions.DataError:
            base.abort(400, _(u'Integrity Error'))

        view_dict = _process_post_data(data, resource_id)

        tags = view_dict.get('tags', '')
        if tags:
            for tag in tags.split(','):
                try:
                    check_access('tag_show', context)
                    tag_obj = get_action('tag_show')(context, {'id': tag})
                except NotFound:
                    check_access('tag_create', context)
                    tag_obj = get_action('tag_create')(context, {
                        'name': tag,
                    })

        to_delete = data.pop('delete', None)

        try:
            if to_delete:
                view_dict['id'] = view_id
                get_action('resource_view_delete')(context, view_dict)
            else:
                view_dict['id'] = view_id
                resource_view = \
                    get_action('resource_view_update')(context, view_dict)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to edit resource'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, resource_id, view_dict, errors, error_summary)

        return h.redirect_to(controller='package',
                             action='resource_views',
                             id=id, resource_id=resource_id)


table_view.add_url_rule(u'/new_table',
                        view_func=CreateView.as_view(str(u'new_table')))
table_view.add_url_rule(u'/edit_table/<view_id>',
                        view_func=EditView.as_view(str(u'edit_table')))
