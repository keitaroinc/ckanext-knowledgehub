import logging
import json

from flask import Blueprint
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request
from ckan.logic import (
    get_action,
    check_access,
    NotAuthorized,
)


log = logging.getLogger(__name__)


access = Blueprint(
    u'access',
    __name__,
    url_prefix='/access',
)


def _get_context():
    return dict(model=model, user=g.user,
                auth_user_obj=g.userobj,
                session=model.Session)


def request(entity_type, entity_ref):
    context = _get_context()
    try:
        check_access('request_access', context, {})
    except NotAuthorized:
        base.abort(403, _('You do not have pemrission to request access '
                          'on this resource.'))
        return

    return base.render('access/request.html', extra_vars={})


access.add_url_rule('/request/<entity_type>/<entity_ref>', view_func=request)
