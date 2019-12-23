import logging
import json
from operator import itemgetter

from flask import Blueprint
from flask.views import MethodView

import ckan.lib.base as base
import ckan.lib.helpers as h
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


chart_view = Blueprint(
    u'chart_view',
    __name__,
    url_prefix=u'/dataset/<id>/resource/<resource_id>'
)


def _process_post_data(data, resource_id):
    print(data)
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

            if 'data_filter_operator_{}'.format(filter_id) in data:
                filter['operator'] = \
                    data.pop('data_filter_operator_{}'.format(filter_id))
            else:
                filter['operator'] = ''

            filters.append(filter)

        config['type'] = \
            data['chart_field_type']
        config['title'] = \
            data['chart_field_title']
        config['chart_subtitle'] = \
            data['chart_field_subtitle']
        config['chart_description'] = \
            data['chart_field_description']
        config['x_axis'] = \
            data['chart_field_x_axis_column']
        config['y_axis'] = \
            data['chart_field_y_axis_column']
        config['additional_tornado_value'] = \
            data['chart_field_additional_tornado_value']
        config['category_name'] = \
            data['chart_field_category_name']
        config['color'] = \
            data['chart_field_color']
        config['y_label'] = \
            data['chart_field_y_label']
        config['x_text_rotate'] = \
            data['chart_field_x_text_rotate']
        if 'chart_field_x_text_multiline' in data:
            config['x_text_multiline'] = 'true'
        else:
            config['x_text_multiline'] = 'false'
        config['dynamic_reference_type'] = \
            data['chart_field_dynamic_reference_type']
        config['dynamic_reference_label'] = \
            data['chart_field_dynamic_reference_label']
        config['dynamic_reference_factor'] = \
            data['chart_field_dynamic_reference_factor']
        config['sort'] = \
            data['chart_field_sort']
        config['chart_padding_left'] = \
            data['chart_field_chart_padding_left']
        config['chart_padding_bottom'] = \
            data['chart_field_chart_padding_bottom']
        config['tick_count'] = \
            data['chart_field_tick_count']
        if 'chart_field_legend' in data:
            config['show_legend'] = 'true'
        else:
            config['show_legend'] = 'false'
        config['padding_top'] = \
            data['chart_field_padding_top']
        config['data_format'] = \
            data['chart_field_data_format']
        config['tooltip_name'] = \
            data['chart_field_tooltip_name']
        if 'chart_field_labels' in data:
            config['show_labels'] = 'true'
        else:
            config['show_labels'] = 'false'
        if 'chart_field_y_from_zero' in data:
            config['y_from_zero'] = 'true'
        else:
            config['y_from_zero'] = 'false'
        config['y_tick_format'] = \
            data['chart_field_y_ticks_format']
        config['sql_string'] = \
            data['sql_string']
        if 'chart_research_questions' in data:
            config['chart_research_questios'] = \
                data['chart_research_questions']

    config['filters'] = json.dumps(filters)

    view_dict = {}
    view_dict['resource_id'] = resource_id
    view_dict['title'] = config['title']
    view_dict['view_type'] = 'chart'
    view_dict.update(config)

    return view_dict


@chart_view.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user,
                       auth_user_obj=g.userobj)
        check_access(u'sysadmin', context)
    except NotAuthorized:
        base.abort(403, _(u'Need to be system '
                          u'administrator to administer'))


class EditView(MethodView):
    u''' Edit existing Chart view '''

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

        filters = json.loads(data['__extras']['filters'])
        filters.sort(key=itemgetter('order'))
        data['__extras']['filters'] = json.dumps(filters)

        vars = {
            'pkg': package,
            'res': resource,
            'data': data,
            'errors': errors,
            'error_summary': error_summary
        }

        return base.render(
            u'view/chart/edit_chart_view_base.html',
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


class CreateView(MethodView):
    u''' Create new Chart view '''

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
            u'view/chart/new_chart_view_base.html',
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


chart_view.add_url_rule(u'/new_chart',
                        view_func=CreateView.as_view(str(u'new_chart')))
chart_view.add_url_rule(u'/edit_chart/<view_id>',
                        view_func=EditView.as_view(str(u'edit_chart')))
