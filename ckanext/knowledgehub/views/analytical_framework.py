import logging

from flask import Blueprint

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
from ckan.common import g, _

log = logging.getLogger(__name__)


analytical_framework = Blueprint(u'analytical_framework', __name__, url_prefix=u'/analytical-framework')

@analytical_framework.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
        logic.check_access(u'sysadmin', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Need to be system administrator to administer'))


def search():
    return base.render(u'analytical_framework/search.html', extra_vars={})



analytical_framework.add_url_rule(u'/', view_func=search, strict_slashes=False)