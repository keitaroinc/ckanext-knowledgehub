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

import uuid
from ckan.tests import factories
from ckan.plugins import toolkit
from ckan import model
from ckan.model.user import User as CkanUser


class User(object):
    def __init__(self, id):
        self.id = id


def create_dataset(**kwargs):
    sysadmin = factories.Sysadmin()
    user = User(sysadmin.get('id'))

    context = {
        'auth_user_obj': user,
        'user': sysadmin.get('name')
    }

    data_dict = {
        'name': 'org1'
    }
    org = toolkit.get_action('organization_create')(context, data_dict)

    data_dict = {
        'name': str(uuid.uuid4()),
        'title': 'title',
        'notes': 'notes',
        'maintainer': 'John',
        'research_question': ['rq', 'rq1'],
        'owner_org': org['name'],
        'archived': 'No',
        'data_collection_technique': 'Tech',
        'unit_of_measurement': 'Unit',
        'data_collector': 'None'

    }
    data_dict.update(kwargs)
    return toolkit.get_action('package_create')(context, data_dict)


def mock_pylons():
    from paste.registry import Registry
    import pylons
    from pylons.util import AttribSafeContextObj
    import ckan.lib.app_globals as app_globals
    from ckan.lib.cli import MockTranslator
    from ckan.config.routing import make_map
    from pylons.controllers.util import Request, Response
    from routes.util import URLGenerator

    class TestPylonsSession(dict):
        last_accessed = None

        def save(self):
            pass

    registry = Registry()
    registry.prepare()

    context_obj = AttribSafeContextObj()
    registry.register(pylons.c, context_obj)

    app_globals_obj = app_globals.app_globals
    registry.register(pylons.g, app_globals_obj)

    request_obj = Request(dict(HTTP_HOST="nohost", REQUEST_METHOD="GET"))
    registry.register(pylons.request, request_obj)

    translator_obj = MockTranslator()
    registry.register(pylons.translator, translator_obj)

    registry.register(pylons.response, Response())
    mapper = make_map()
    registry.register(pylons.url, URLGenerator(mapper, {}))
    registry.register(pylons.session, TestPylonsSession())


def get_context():
    user = factories.Sysadmin()
    auth_user_obj = CkanUser.get(user['id'])
    return {
        'user': user.get('name'),
        'auth_user_obj': auth_user_obj,
        'ignore_auth': True,
        'model': model,
        'session': model.Session
    }


def get_regular_user_context():
    user = factories.User()
    auth_user_obj = CkanUser.get(user['id'])
    return {
        'user': user.get('name'),
        'auth_user_obj': auth_user_obj,
        'model': model,
        'session': model.Session,
        'ignore_auth': True,
    }
