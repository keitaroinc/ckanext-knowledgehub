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

        # TODO handle items order
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

    if len(filters) > 0:
        filters.sort(key=itemgetter('order'))
    config['filters'] = json.dumps(filters)

    view_dict = {}
    view_dict['resource_id'] = resource_id
    view_dict['title'] = config['title']
    view_dict['view_type'] = 'table'
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
            'res': resource,
            'data_type': 'quantitative'
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


table_view.add_url_rule(u'/new_table',
                        view_func=CreateView.as_view(str(u'new_table')))
