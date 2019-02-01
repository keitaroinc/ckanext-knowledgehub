# -*- coding: utf-8 -*-
import logging

import ckan.plugins.toolkit as toolkit

from ckanext.knowledgehub.backend.mssql import MssqlBackend


log = logging.getLogger(__name__)

ValidationError = toolkit.ValidationError

_SUPPORTED_BACKENDS = [u'mssql',
                       u'postgresql'
                       ]

_backends = {
    u'mssql': MssqlBackend(),
    u'postgresql': None
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
    return _backends[type]
