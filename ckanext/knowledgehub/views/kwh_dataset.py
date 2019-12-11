# encoding: utf-8
import logging
import datetime
from werkzeug.datastructures import FileStorage as FlaskFileStorage

from flask import Blueprint
from flask.views import MethodView
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request
from ckanext.knowledgehub.lib.writer import WriterService

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
    err_msg = ''

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
            else:
                diff = [f['id'] for f in current_fields if f not in fields]
                diff.extend(
                    [f['id'] for f in fields if f not in current_fields]
                )
                err_msg = ('The format of the data resources is different. '
                           'Resource {resource} differs from the rest, '
                           'fields: {fields}').format(
                               resource=resource.get('name'),
                               fields=", ".join(diff)
                            )
    if records:
            writer = WriterService()
            stream = writer.csv_writer(fields, records, ',')

            filename = '{}_{}.{}'.format(
                package.get('name'),
                str(datetime.datetime.utcnow()),
                'csv'
            )

            data_dict = {
                'package_id': id,
                'name': filename,
                'upload':  FlaskFileStorage(stream, filename)
            }

            rsc = get_action('resource_create')(context, data_dict)

    return h.redirect_to(controller='package',
                         action='read',
                         id=id,
                         error_message=err_msg)


kwh_dataset.add_url_rule(u'/merge_all_data/<id>', view_func=merge_all_data)
