import logging

from flask import Blueprint
from flask.views import MethodView

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
from ckan.common import g, _, request

log = logging.getLogger(__name__)


analytical_framework = Blueprint(
    u'analytical_framework',
    __name__,
    url_prefix=u'/analytical-framework'
)


@analytical_framework.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
        logic.check_access(u'sysadmin', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Need to be system administrator to administer'))


def search():
    # TODO: implement
    return base.render(u'analytical_framework/search.html', extra_vars={})


def read(id):
    # TODO: implement
    return base.render(u'analytical_framework/read.html', extra_vars={})


class CreateView(MethodView):
    u''' Create new Analytical Framework view '''

    def _is_save(self):
        return u'save' in request.form

    def _prepare(self, data=None):

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj,
            u'save': self._is_save()
        }
        try:
            logic.check_access(u'package_create', context)
        except logic.NotAuthorized:
            return base.abort(403, _(u'Unauthorized to create a package'))
        return context

    def get(self):
        # TODO: implement
        return base.render(
            u'analytical_framework/base_form_page.html',
            extra_vars={}
        )

    def post(self):
        # TODO: implement
        pass


analytical_framework.add_url_rule(
    u'/', view_func=search, strict_slashes=False)
analytical_framework.add_url_rule(
    u'/new', view_func=CreateView.as_view(str(u'new')))
