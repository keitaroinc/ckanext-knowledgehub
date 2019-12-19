# encoding: utf-8
import logging
import datetime
from werkzeug.datastructures import FileStorage as FlaskFileStorage

from flask import Blueprint
import ckan.logic as logic
import ckan.model as model
from ckan.common import g
import ckan.lib.helpers as h
from ckan.plugins.toolkit import StopOnError

from ckanext.knowledgehub import helpers as kwh_h

get_action = logic.get_action

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
    u''' Merge data resources that belongs to the dataset and create
    new data resource with the whole data
    '''

    try:
        data_dict = get_action('merge_all_data')(
            _get_context(),
            {'id': id}
        )
    except Exception as e:
        data_dict['err_msg'] = 'Unable to merge data'

    return h.redirect_to(controller='package',
                         action='read',
                         id=id,
                         error_message=data_dict.get('err_msg', ''))


kwh_dataset.add_url_rule(u'/merge_all_data/<id>', view_func=merge_all_data)
