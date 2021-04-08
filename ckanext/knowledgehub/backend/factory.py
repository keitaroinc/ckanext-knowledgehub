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

# -*- coding: utf-8 -*-
import logging

import ckan.plugins.toolkit as toolkit

from ckanext.knowledgehub.backend.mssql import MssqlBackend
from ckanext.knowledgehub.backend.postgresql import PostgresqlBackend


log = logging.getLogger(__name__)

ValidationError = toolkit.ValidationError

_SUPPORTED_BACKENDS = [u'mssql',
                       u'postgresql'
                       ]

_backends = {
    u'mssql': MssqlBackend,
    u'postgresql': PostgresqlBackend
}


def get_backend(data_dict):
    """Return appropriate backend
    if supported

    :param db_type: Backend type
    :type db_type: string

    :returns: Backend instance
    :rtype: object

    """
    type = toolkit.get_or_bust(data_dict, 'db_type')

    if type not in _SUPPORTED_BACKENDS:
        raise ValidationError({
            'backend': [u'"{0}" backend type not supported'.format(type)]
        })
    return _backends[type]()
