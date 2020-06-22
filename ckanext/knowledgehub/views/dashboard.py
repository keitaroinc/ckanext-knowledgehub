# encoding: utf-8
import logging
import json

from flask import Blueprint
from flask.views import MethodView
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request
from ckan.controllers.admin import get_sysadmins

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

log = logging.getLogger(__name__)


dashboard = Blueprint(
    u'dashboards',
    __name__,
    url_prefix=u'/dashboards'
)


def _get_context():
    return dict(model=model, user=g.user,
                auth_user_obj=g.userobj,
                session=model.Session)


def index():
    u''' dashboards index view function '''

    extra_vars = {}

    context = _get_context()

    try:
        check_access(u'dashboard_list', context)
    except NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    page = h.get_page_number(request.params) or 1
    items_per_page = int(config.get(u'ckanext.'
                                    u'knowledgehub.dashboards_per_page',
                                    10))
    q = request.params.get(u'q', u'')
    sort_by = request.params.get(u'sort', u'name asc')

    data_dict_global_results = {
        u'q': q,
        u'sort': sort_by
    }

    data_dict_page_results = {
        u'q': q,
        u'sort': sort_by,
        u'limit': items_per_page,
        u'offset': items_per_page * (page - 1)
    }

    extra_vars["q"] = q
    extra_vars["sort_by_selected"] = sort_by

    global_results = get_action(u'dashboard_list')(context,
                                                   data_dict_global_results)

    context.pop('ignore_auth', None)
    context.pop('__auth_user_obj_checked', None)

    page_results = get_action(u'dashboard_list')(context,
                                                 data_dict_page_results)

    extra_vars["page"] = h.Page(
        collection=global_results['data'],
        page=page,
        url=h.pager_url,
        items_per_page=items_per_page)

    extra_vars['page'].items = page_results['data']

    return base.render(u'dashboard/index.html',
                       extra_vars=extra_vars)


def view(name):
    u''' Dashboard view function '''

    context = _get_context()

    extra_vars = {}

    data_dict = {u'name': name}

    try:
        dashboard_dict = get_action(u'dashboard_show')(context, data_dict)
    except NotFound:
        base.abort(404, _(u'Dashboard not found'))
    except NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    if dashboard_dict.get('type') == 'internal':
        dashboard_dict['indicators'] = json.loads(dashboard_dict['indicators'])

        for ind in dashboard_dict['indicators']:
            res_view_id = ind.get('resource_view_id')
            if res_view_id:
                try:
                    res_view = get_action('resource_view_show')({
                        'ignore_auth': True
                    }, {
                        'id': res_view_id
                    })
                    ind['resource_view'] = res_view
                except Exception as e:
                    log.warning('Cannot access resource view %s. Error: %s',
                                res_view_id, str(e))
                    log.exception(e)
                    ind['resource_view_error'] = _('Failed to load visualization.')

    extra_vars['dashboard'] = dashboard_dict

    return base.render(u'dashboard/view.html', extra_vars=extra_vars)


def delete(id):
    u''' Dashboard delete function '''
    context = _get_context()
    try:
        check_access(u'dashboard_delete', context)
    except NotAuthorized:
        return base.abort(403, _(u'Unauthorized'
                                 u' to delete a theme'))

    data_dict = {u'id': id}

    try:
        if request.method == u'POST':
            get_action(u'dashboard_delete')(
                context, data_dict)
            h.flash_notice(_(u'Dashboard has been deleted.'))
    except NotFound:
        base.abort(404, _(u'Dashboard not found'))
    except ValidationError as e:
        h.flash_error(e.error_dict['message'])
        return h.redirect_to(u'dashboards.edit',
                             name=id)

    return h.redirect_to(u'dashboards.index')


class CreateView(MethodView):
    u''' Create new Dashboard view '''

    def _prepare(self):

        context = dict(model=model, user=g.user,
                       auth_user_obj=g.userobj,
                       session=model.Session)
        try:
            check_access(u'dashboard_create', context)
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized'
                                     u' to create a dashboard'))
        return context

    def get(self, data={}, errors=None, error_summary=None):
        return base.render(
            u'dashboard/base_form_page.html',
            extra_vars={'data': data,
                        'errors': errors,
                        'error_summary': error_summary
                        }
        )

    def post(self):
        context = self._prepare()

        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(
                    parse_params(request.form))))

            shared_with_users = data_dict.get('shared_with_users')
            if shared_with_users:
                data_dict['shared_with_users'] = shared_with_users

            if data_dict.get('type') == 'internal':
                indicators = []
                for k, v in data_dict.items():
                    item = {}

                    if k.startswith('research_question'):
                        id = k.split('_')[-1]

                        item['order'] = int(id)
                        item['research_question'] = \
                            data_dict['research_question_{}'.format(id)]
                        item['resource_view_id'] = \
                            data_dict['visualization_{}'.format(id)]
                        item['size'] = data_dict['size_{}'.format(id)]

                        indicators.append(item)

                data_dict['indicators'] = json.dumps(indicators)
            else:
                indicators = data_dict.get('indicators')
                if indicators:
                    rq_indicators = []
                    if isinstance(indicators, list):
                        for ind in indicators:
                            rq_indicators.append({
                                'research_question': ind
                            })
                    elif isinstance(indicators, unicode):
                        rq_indicators.append({
                            'research_question': indicators
                        })

                    data_dict['indicators'] = json.dumps(rq_indicators)

            dashboard = get_action(u'dashboard_create')(
                context, data_dict)
        except dict_fns.DataError:
            base.abort(400, _(u'Integrity Error'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary

            if data_dict.get('type') == 'internal':
                data_dict['indicators'] = json.loads(data_dict['indicators'])

                for ind in data_dict['indicators']:
                    res_view_id = ind.get('resource_view_id')
                    try:
                        res_view = get_action('resource_view_show')(
                            _get_context(),
                            {
                                'id': res_view_id
                            })
                        ind['resource_view'] = res_view
                    except Exception as e:
                        log.warning('Cannot access resource view %s. '
                                    'Error: %s', res_view_id, str(e))
                        log.exception(e)

                    viz_options = [{
                        'text': 'Choose visualization',
                        'value': '',
                    }]
                    try:
                        rq = get_action('research_question_show')(
                            _get_context(),
                            {
                                'id': ind['research_question']
                            }
                        )

                        visualizations = get_action('visualizations_for_rq')(
                            _get_context(),
                            {
                                'research_question': rq['id']
                            })

                        for viz in visualizations:
                            viz_options.append({
                                'text': viz.get('title'),
                                'value': viz.get('id'),
                            })
                    except Exception as e:
                        log.warning('Failed to fetch reserch questions and '
                                    'visualizations. Error: %s', str(e))
                        log.exception(e)
                    ind['viz_options'] = viz_options

            return self.get(data_dict,
                            errors,
                            error_summary)

        return h.redirect_to(u'dashboards.index')


class EditView(MethodView):
    u''' Edit Dashboard view '''

    def _prepare(self, name):

        data_dict = {u'name': name}
        context = _get_context()

        try:
            check_access(u'dashboard_update', context)
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized'
                                     u' to update dashboard'))
        except NotFound:
            base.abort(404, _(u'Dashboard not found'))
        return context

    def get(self, name, data=None, errors=None,
            error_summary=None):

        context = self._prepare(name)
        data_dict = {u'name': name}

        try:
            old_data = get_action(u'dashboard_show')(
                context, data_dict)
            data = data or old_data
        except NotFound:
            base.abort(404, _(u'Dashboard not found'))

        dashboard = data
        errors = errors or {}

        if data.get('type') == 'internal':
            data['indicators'] = json.loads(data['indicators'])

            for ind in data['indicators']:
                res_view_id = ind.get('resource_view_id')
                if res_view_id:
                    try:
                        res_view = get_action('resource_view_show')(
                            _get_context(),
                            {
                                'id': res_view_id
                            })
                        ind['resource_view'] = res_view
                    except Exception as e:
                        log.warning('Cannot access resource view %s. '
                                    'Error: %s', res_view_id, str(e))
                try:
                    rq = get_action('research_question_show')(
                        _get_context(),
                        {
                            'id': ind['research_question']
                        }
                    )

                    viz_options = [{
                        'text': 'Choose visualization',
                        'value': '',
                    }]
                    visualizations = get_action('visualizations_for_rq')(
                        _get_context(),
                        {
                            'research_question': rq['id']
                        })

                    for viz in visualizations:
                        viz_options.append({
                            'text': viz.get('title'),
                            'value': viz.get('id'),
                        })

                    ind['viz_options'] = viz_options
                except Exception as e:
                    ind['viz_options'] = []
                    log.warning('Failed to load visualizations for research '
                                'question. Error: %s', str(e))
                    log.exception(e)
        else:
            if data.get('indicators'):
                data['indicators'] = json.loads(data['indicators'])

        return base.render(
            u'dashboard/edit_form_page.html',
            extra_vars={'data': data, 'errors': errors,
                        'error_summary': error_summary,
                        'dashboard': dashboard}
        )

    def post(self, name):

        context = self._prepare(name)

        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(
                    parse_params(request.form)
                ))
            )

            shared_with_users = data_dict.get('shared_with_users')
            if shared_with_users:
                data_dict['shared_with_users'] = shared_with_users

            if data_dict.get('type') == 'internal':
                indicators = []
                for k, v in data_dict.items():
                    item = {}

                    if k.startswith('research_question'):
                        id = k.split('_')[-1]

                        item['order'] = int(id)
                        item['research_question'] = \
                            data_dict['research_question_{}'.format(id)]
                        item['resource_view_id'] = \
                            data_dict['visualization_{}'.format(id)]
                        item['size'] = data_dict['size_{}'.format(id)]

                        indicators.append(item)

                data_dict['indicators'] = json.dumps(indicators)
            else:
                indicators = data_dict.get('indicators')
                if indicators:
                    rq_indicators = []
                    if isinstance(indicators, list):
                        for ind in indicators:
                            rq_indicators.append({
                                'research_question': ind
                            })
                    elif isinstance(indicators, unicode):
                        rq_indicators.append({
                            'research_question': indicators
                        })

                    data_dict['indicators'] = json.dumps(rq_indicators)

            dashboard = get_action(u'dashboard_update')(
                context, data_dict)
            h.flash_notice(_(u'Dashboard has been updated.'))
        except dict_fns.DataError:
            base.abort(400, _(u'Integrity Error'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary

            if data_dict.get('type') == 'internal':
                data_dict['indicators'] = json.loads(data_dict['indicators'])

                for ind in data_dict['indicators']:
                    res_view_id = ind.get('resource_view_id')
                    res_view = get_action('resource_view_show')(
                        _get_context(),
                        {
                            'id': res_view_id
                        })
                    ind['resource_view'] = res_view

                    viz_options = [{
                        'text': 'Choose visualization',
                        'value': ''
                    }]
                    try:
                        rq = get_action('research_question_show')(
                            _get_context(),
                            {
                                'id': ind['research_question']
                            })

                        visualizations = get_action('visualizations_for_rq')(
                            _get_context(),
                            {
                                'research_question': rq['id']
                            })

                        for viz in visualizations:
                            viz_options.append({
                                'text': viz.get('title'),
                                'value': viz.get('id'),
                            })
                    except Exception as e:
                        ind['viz_options'] = []
                        log.warning('Failed to fetch visualizations for '
                                    'research question. Error: %s', str(e))
                        log.exception(e)
                    ind['viz_options'] = viz_options

            return self.get(name, data_dict,
                            errors, error_summary)

        return h.redirect_to(u'dashboards.index')


dashboard.add_url_rule(u'/', view_func=index, strict_slashes=False)
dashboard.add_url_rule(u'/new', view_func=CreateView.as_view(str(u'new')))
dashboard.add_url_rule(u'/<name>/view', methods=[u'GET'], view_func=view)
dashboard.add_url_rule(u'/edit/<name>',
                       view_func=EditView.as_view(str(u'edit')))
dashboard.add_url_rule(u'/delete/<id>', methods=[u'POST'], view_func=delete)
