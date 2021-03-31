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

# encoding: utf-8
import logging

from flask import Blueprint
from flask.views import MethodView
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

log = logging.getLogger(__name__)


theme = Blueprint(
    u'theme',
    __name__,
    url_prefix=u'/theme'
)


def _get_context():
    return dict(model=model, user=g.user,
                auth_user_obj=g.userobj,
                session=model.Session)


def index():
    u''' Themes index view function '''

    extra_vars = {}

    context = _get_context()

    # TODO add appropriate check
    # try:
    #     check_access(u'theme_list', context)
    # except NotAuthorized:
    #     base.abort(403, _(u'Not authorized to see this page'))

    page = h.get_page_number(request.params) or 1
    items_per_page = int(config.get(u'ckanext.'
                                    u'knowledgehub.themes_per_page',
                                    10))
    q = request.params.get(u'q', u'')
    sort_by = request.params.get(u'sort', u'name asc')

    data_dict_global_results = {
        u'q': q,
        u'sort': sort_by
    }

    data_dict_page_results = {
        u'q': q,
        u'sort': sort_by,
        u'limit': items_per_page,
        u'offset': items_per_page * (page - 1)
    }

    extra_vars["q"] = q
    extra_vars["sort_by_selected"] = sort_by

    global_results = get_action(u'theme_list')(context,
                                               data_dict_global_results)

    page_results = get_action(u'theme_list')(context,
                                             data_dict_page_results)

    extra_vars["page"] = h.Page(
        collection=global_results['data'],
        page=page,
        url=h.pager_url,
        items_per_page=items_per_page, )

    extra_vars['page'].items = page_results['data']

    return base.render(u'theme/index.html',
                       extra_vars=extra_vars)


def read(name):
    u''' Theme read item view function '''

    # TODO add appropriate check
    # try:
    #     check_access(u'theme_list', context)
    # except NotAuthorized:
    #     base.abort(403, _(u'Not authorized to see this page'))

    extra_vars = {}

    data_dict = {u'name': name}
    context = _get_context()

    try:
        theme_dict = get_action(u'theme_show')(context,
                                               data_dict)
    except (NotFound, NotAuthorized):
        base.abort(404, _(u'Theme not found'))

    extra_vars['theme'] = theme_dict

    return base.render(u'theme/read.html',
                       extra_vars=extra_vars)


def delete(id):
    u''' Theme delete view function '''
    context = _get_context()
    try:
        check_access(u'theme_delete', context)
    except NotAuthorized:
        return base.abort(403, _(u'Unauthorized'
                                 u' to create a theme'))

    data_dict = {u'id': id}

    try:
        if request.method == u'POST':
            get_action(u'theme_delete')(
                context, data_dict)
            h.flash_notice(_(u'Theme has been deleted.'))
    except NotAuthorized:
        base.abort(403, _(u'Unauthorized to delete theme.'))
    except NotFound:
        base.abort(404, _(u'Theme not found'))
    except ValidationError as e:
        h.flash_error(e.error_dict['message'])
        return h.redirect_to(u'theme.edit',
                             name=id)

    return h.redirect_to(u'theme.index')


class CreateView(MethodView):
    u''' Create new Theme view '''

    def _prepare(self):

        context = dict(model=model, user=g.user,
                       auth_user_obj=g.userobj,
                       session=model.Session)
        try:
            check_access(u'theme_create', context)
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized'
                                     u' to create a theme'))
        return context

    def get(self, data=None, errors=None,
            error_summary=None):

        return base.render(
            u'theme/base_form_page.html',
            extra_vars={'data': data,
                        'errors': errors,
                        'error_summary': error_summary
                        }
        )

    def post(self):

        context = self._prepare()
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(
                    parse_params(request.form))))

            theme = get_action(u'theme_create')(
                context, data_dict)

        except dict_fns.DataError:
            base.abort(400, _(u'Integrity Error'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(data_dict,
                            errors,
                            error_summary)

        return h.redirect_to(u'theme.read',
                             name=theme['name'])


class EditView(MethodView):
    u''' Edit Theme view '''

    def _prepare(self, name):

        data_dict = {u'name': name}
        context = _get_context()

        try:
            theme = get_action(u'theme_show')(
                context, data_dict)
            check_access(u'theme_update', context)
            context['id'] = theme['id']
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized'
                                     u' to update theme'))
        except NotFound:
            base.abort(404, _(u'Theme not found'))
        return context

    def get(self, name, data=None, errors=None,
            error_summary=None):

        context = self._prepare(name)
        data_dict = {u'name': name}

        try:
            old_data = get_action(u'theme_show')(
                context, data_dict)
            data = data or old_data
        except (NotFound, NotAuthorized):
            base.abort(404, _(u'Theme not found'))

        theme = data
        errors = errors or {}

        return base.render(
            u'theme/edit_form_page.html',
            extra_vars={'data': data, 'errors': errors,
                        'error_summary': error_summary,
                        'theme': theme}
        )

    def post(self, name):

        context = self._prepare(name)

        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(
                    parse_params(request.form)
                ))
            )
            data_dict['id'] = context['id']

            theme = get_action(u'theme_update')(
                context, data_dict)
            h.flash_notice(_(u'Theme has been updated.'))

        except dict_fns.DataError:
            base.abort(400, _(u'Integrity Error'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(name, data_dict,
                            errors, error_summary)

        return h.redirect_to(u'theme.read', name=theme['name'])


theme.add_url_rule(u'/', view_func=index,
                   strict_slashes=False)
theme.add_url_rule(u'/new',
                   view_func=CreateView.as_view(str(u'new')))
theme.add_url_rule(u'/edit/<name>',
                   view_func=EditView.as_view(str(u'edit')))
theme.add_url_rule(u'/<name>',
                   methods=[u'GET'], view_func=read)
theme.add_url_rule(u'/delete/<id>',
                   methods=[u'POST'], view_func=delete)
