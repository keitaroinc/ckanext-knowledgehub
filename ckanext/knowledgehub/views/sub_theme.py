import logging

from flask import Blueprint
from flask.views import MethodView

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
from ckan.common import g, _, request, config
from ckan.lib.navl import dictization_functions

log = logging.getLogger(__name__)

new_sub_theme_form = u'sub_theme/new_sub_theme_form.html'

sub_theme = Blueprint(
    u'sub_theme',
    __name__,
    url_prefix=u'/sub-theme'
)

@sub_theme.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
        logic.check_access(u'sysadmin', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Need to be system administrator to administer'))

def search():
    q = request.params.get(u'q', u'')
    page = request.params.get(u'page', 1)
    order_by = request.params.get(u'sort', u'name desc')
    limit = int(
        request.params.get(u'limit', config.get(u'ckanext.knowledgehub.sub_theme_limit', 2)))

    data_dict = {
        u'q': q,
        u'order_by': order_by,
        u'pageSize': limit,
        u'page': page
    }

    try:
        sub_themes = logic.get_action(u'sub_theme_list')({}, data_dict)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    page = h.Page(
        collection=sub_themes.get(u'data', []),
        page=page,
        url=h.pager_url,
        item_count=sub_themes.get(u'total', 0),
        items_per_page=limit)


    return base.render(
        u'sub_theme/search.html',
        extra_vars={
            u'total': sub_themes.get('total', 0),
            u'sub_themes': sub_themes.get('data', []),
            u'q': q,
            u'order_by': order_by,
            u'page': page
        })

def read(id):
    # TODO: implement
    return base.render(u'sub_theme/read.html', extra_vars={})


class CreateView(MethodView):
    ''' Create new Sub-theme view '''

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
            logic.check_access(u'sub_theme_create', context)
        except logic.NotAuthorized:
            return base.abort(403, _(u'Unauthorized to create a sub-theme'))
        return context

    def get(self, data=None, errors=None, error_summary=None):
        context = self._prepare()

        theme_options = []
        themes = logic.get_action(u'theme_list')(context, {})
        for theme in themes.get(u'data', []):
            opt = {u'text': theme[u'title'], u'value': theme[u'id']}
            theme_options.append(opt)

        form_vars = {
            u'data': data or {},
            u'theme_options': theme_options,
            u'errors': errors or {},
            u'error_summary': error_summary or {}
        }

        extra_vars = {
            u'form': base.render(new_sub_theme_form, form_vars)
        }

        return base.render(u'sub_theme/new.html', extra_vars)

    def post(self):
        context = self._prepare()

        try:
            data_dict = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.form))))
        except dictization_functions.DataError:
            base.abort(400, _(u'Integrity Error'))

        try:
            sub_theme = logic.get_action(u'sub_theme_create')(context, data_dict)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to create a sub-theme'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(data_dict, errors, error_summary)

        return h.redirect_to(u'sub_theme.read', id=sub_theme.get(u'id'))



sub_theme.add_url_rule(u'/', view_func=search, strict_slashes=False)
sub_theme.add_url_rule(u'/new', view_func=CreateView.as_view(str(u'new')))
sub_theme.add_url_rule(u'/<id>', view_func=read)
