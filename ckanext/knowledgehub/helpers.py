import logging
import os
import pkgutil
import inspect

from flask import Blueprint

import ckan.plugins.toolkit as toolkit
import ckan.model as model
from ckan.common import g
from ckan import logic


log = logging.getLogger(__name__)


def _get_context():
    context = dict(model=model,
                   user=g.user,
                   auth_user_obj=g.userobj)
    return context


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


def get_rq_options():
    context = _get_context()
    rq_options = []
    rq_list = toolkit.get_action('research_question_list')(context, {})

    for rq in rq_list.get(u'data', []):
        opt = {u'text': rq[u'title'], u'value': rq[u'title']}
        rq_options.append(opt)
    return rq_options


def get_theme_options():
    context = _get_context()
    theme_options = []
    theme_list = toolkit.get_action('theme_list')(context, {})
    for theme in theme_list.get(u'data', []):
        opt = {u'text': theme[u'title'], u'value': theme[u'title']}
        theme_options.append(opt)
    theme_options.insert(0, {'text': 'Select theme', 'value': ''})
    return theme_options


def get_sub_theme_options():
    context = _get_context()
    sub_theme_options = []
    sub_theme_list = toolkit.get_action('sub_theme_list')(context, {})
    for sub_theme in sub_theme_list.get(u'data', []):
        opt = {u'text': sub_theme[u'title'], u'value': sub_theme[u'title']}
        sub_theme_options.append(opt)
    sub_theme_options.insert(0, {'text': 'Select sub-theme', 'value': ''})
    return sub_theme_options


def pg_array_to_py_list(rq_list):

    if rq_list.startswith('{'):
        ids = rq_list.replace('{', '').replace('}', '').split(',')
    else:
        ids = [rq_list]
    return ids

#    @core_helper
def resource_view_get_fields(resource):
    '''Returns sorted list of text and time fields of a datastore resource.'''

    if not resource.get('datastore_active'):
        return []

    data = {
        'resource_id': resource['id'],
        'limit': 0
    }
#   result = logic.get_action('datastore_search')({}, data)
    try:
        result = logic.get_action('datastore_search')({}, data)
        fields = [field['id'] for field in result.get('fields', [])]

#    fields = [field['id'] for field in result.get('fields', [])]
        return sorted(fields)

#    return sorted(fields)
    except logic.NotFound:
        return []
