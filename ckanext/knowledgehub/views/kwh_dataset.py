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
    data_dict = {}
    try:
        data_dict = get_action('merge_all_data')(
            _get_context(),
            {'id': id}
        )
    except Exception as e:
        note = 'Unable to merge data: '
        error_msg = str(e)
        data_dict['err_msg'] = note + error_msg

    return h.redirect_to(controller='package',
                         action='read',
                         id=id,
                         error_message=data_dict.get('err_msg', ''))


kwh_dataset.add_url_rule(u'/merge_all_data/<id>', view_func=merge_all_data)
