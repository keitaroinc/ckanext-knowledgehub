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


chart_view = Blueprint(
    u'chart_view',
    __name__,
    url_prefix=u'/dataset/<id>/resource/<resource_id>'
)


@chart_view.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user,
                       auth_user_obj=g.userobj)
        check_access(u'sysadmin', context)
    except NotAuthorized:
        base.abort(403, _(u'Need to be system '
                          u'administrator to administer'))


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
        data = data or {}

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
        filters = []

        if 'config' in data:
            if 'filters' in data['config']:
                filters = data['config']['filters']
                filters.sort(key=itemgetter('order'))

        vars = {
            'data': data,
            'filters': filters,
            'errors': errors,
            'error_summary': error_summary,
            'pkg': package,
            'res': resource
        }

        return base.render(
            u'view/chart/new_chart_form.html',
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

        config['filters'] = filters
        data['config'] = config

        log.info('Create chart view')
        return self.get(id, resource_id, data)


chart_view.add_url_rule(u'/new_chart',
                        view_func=CreateView.as_view(str(u'new_chart')))
