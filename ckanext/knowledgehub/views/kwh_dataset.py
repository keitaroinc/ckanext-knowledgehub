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


kwh_dataset = Blueprint(
    u'kwh_dataset',
    __name__,
    url_prefix=u'/kwh_dataset'
)


def _get_context():
    return dict(model=model, user=g.user,
                auth_user_obj=g.userobj,
                session=model.Session)


def merge_all_data(id):
    u''' Merge data resources that belongs to the dataset'''

    context = _get_context()
    fields = []
    records = []

    package = get_action('package_show')(
        context,
        {'id': id})
    resources = package.get('resources', [])

    if len(resources):
        for resource in resources:
            sql = 'SELECT * FROM "{resource}"'.format(
                resource=resource.get('id'))
            try:
                result = get_action('datastore_search_sql')(
                    context,
                    {'sql': sql})
                if len(fields) == 0:
                    fields = result.get('fields', [])
                    records = result.get('records', [])
                    continue

                current_fields = result.get('fields', [])
            except Exception as e:
                log.debug(str(e))
                continue

            if fields == current_fields:
                records.extend(result.get('records', []))
                print records
            else:
                print "The format of the data resources is different."

    return h.redirect_to(controller='package', action='read', id=id)


kwh_dataset.add_url_rule(u'/merge_all_data/<id>', view_func=merge_all_data)
