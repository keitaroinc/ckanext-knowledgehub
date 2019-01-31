import logging
import os
import pkgutil
import inspect

from flask import Blueprint

import ckan.plugins.toolkit as toolkit
from ckan import logic


log = logging.getLogger(__name__)


def _register_blueprints():
    u'''Return all blueprints defined in the `views` folder
    '''
    blueprints = []

    def is_blueprint(mm):
        return isinstance(mm, Blueprint)

    path = os.path.join(os.path.dirname(__file__), 'views')

    for loader, name, _ in pkgutil.iter_modules([path]):
        module = loader.find_module(name).load_module(name)
        for blueprint in inspect.getmembers(module, is_blueprint):
            blueprints.append(blueprint[1])
            log.debug(u'Registered blueprint: {0!r}'.format(blueprint[0]))
    return blueprints


def _get_functions(module_root, functions={}):
    u'''
     Helper function that scans extension
     specified dir for all functions.
     '''
    for module_name in ['create', 'update', 'delete', 'get']:
        module_path = '%s.%s' % (module_root, module_name,)

        module = __import__(module_path)

        for part in module_path.split('.')[1:]:
            module = getattr(module, part)

        for key, value in module.__dict__.items():
            if not key.startswith('_') \
                    and (hasattr(value, '__call__')
                         and (value.__module__ == module_path)):
                functions[key] = value

    return functions


def id_to_title(model, id):
    data_dict = {}
    data_dict['id'] = id
    if model:
        entry = toolkit.get_action('{}_show'.format(model))({}, data_dict)
    return entry.get('title') or entry.get('name')
