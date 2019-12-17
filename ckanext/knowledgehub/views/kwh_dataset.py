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
from ckanext.knowledgehub import helpers as kwh_h

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


def _get_dataset_data(id):
    u''' Return fields and records from all data resource for given package ID
    '''
    data_dict = {
        'fields': [],
        'records': [],
        'package_name': '',
        'err_msg': '',
        'all_months_resource': {}
    }
    context = _get_context()

    try:
        package = get_action('package_show')(context, {'id': id})
        data_dict['package_name'] = package.get('name')
    except Exception as e:
        log.error(e, exc_info=True)
        data_dict['err_msg'] = 'Internal server error'
        return data_dict

    resources = package.get('resources', [])
    if len(resources):
        for resource in resources:
            rsc_id = resource.get('id')
            rsc_name = resource.get('name')

            if rsc_name == '{}_all_months'.format(data_dict['package_name']):
                data_dict['all_months_resource'] = resource
                continue

            sql = 'SELECT * FROM "{resource}"'.format(
                resource=rsc_id)
            try:
                result = get_action('datastore_search_sql')(
                    context,
                    {'sql': sql})

                if len(data_dict['fields']) == 0:
                    data_dict['fields'] = result.get('fields', [])
                    data_dict['records'] = result.get('records', [])
                    continue
                else:
                    current_fields = result.get('fields', [])
            except Exception as e:
                log.error('Failed to query the datastore: %s',
                          e,
                          exc_info=True)
                data_dict['err_msg'] = 'Internal server error'
                return data_dict

            if data_dict['fields'] == current_fields:
                current_results = []
                for r in result.get('records'):
                    row = {}
                    for k, v in r.items():
                        if k not in ['_id', '_full_text']:
                            row[k] = v
                    current_results.append(row)
                data_dict['records'].extend(current_results)
            else:
                diff = [f['id'] for f in current_fields
                        if f not in data_dict['fields']]
                diff.extend([f['id'] for f in data_dict['fields']
                             if f not in current_fields])
                data_dict['err_msg'] = ('The format of the data resource '
                                        '{resource} differs from the others, '
                                        'fields: {fields}').format(
                                            resource=rsc_name,
                                            fields=", ".join(diff))
                break

        data_dict['fields'] = [f for f in data_dict['fields']
                               if f['id'] not in ['_id', '_full_text']]

        return data_dict


def merge_all_data(id):
    u''' Merge data resources that belongs to the dataset and create
    new data resource with the entire data
    '''

    data_dict = _get_dataset_data(id)

    if data_dict['records'] and not data_dict['err_msg']:
            writer = WriterService()
            stream = writer.csv_writer(
                data_dict['fields'], data_dict['records'], ',')

            filename = '{}_{}.{}'.format(
                data_dict['package_name'],
                str(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')),
                'csv'
            )

            rsc_dict = {
                'package_id': id,
                'name': '{}_all_months'.format(data_dict['package_name']),
                'upload':  FlaskFileStorage(stream, filename)
            }

            try:
                if data_dict['all_months_resource']:
                    rsc_dict['id'] = data_dict['all_months_resource']['id']
                    rsc = get_action('resource_update')(
                        _get_context(), rsc_dict)
                else:
                    rsc = get_action('resource_create')(
                        _get_context(), rsc_dict)

            except Exception as e:
                log.error(e, exc_info=True)
                data_dict['err_msg'] = 'Internal server error'

    return h.redirect_to(controller='package',
                         action='read',
                         id=id,
                         error_message=data_dict['err_msg'])


kwh_dataset.add_url_rule(u'/merge_all_data/<id>', view_func=merge_all_data)
