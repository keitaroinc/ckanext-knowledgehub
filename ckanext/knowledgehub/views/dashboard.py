# encoding: utf-8
import logging

from flask import Blueprint
from flask.views import MethodView
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request

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


def index():
    u''' dashboards index view function '''

    extra_vars = {}

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }

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


dashboard.add_url_rule(u'/', view_func=index, strict_slashes=False)
