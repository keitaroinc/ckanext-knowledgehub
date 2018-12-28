import logging
import os
import pkgutil
import inspect

from flask import Blueprint

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