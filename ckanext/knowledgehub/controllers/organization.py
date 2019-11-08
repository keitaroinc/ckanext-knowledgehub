# encoding: utf-8

import logging
from urllib import urlencode

from pylons.i18n import get_lang
from six import string_types, text_type
from ckan.controllers.organization import OrganizationController

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model
import ckan.authz as authz
import ckan.lib.plugins
import ckan.plugins as plugins
from ckan.common import OrderedDict, c, config, request, _

log = logging.getLogger(__name__)

render = base.render
abort = base.abort

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

lookup_group_plugin = ckan.lib.plugins.lookup_group_plugin
lookup_group_controller = ckan.lib.plugins.lookup_group_controller

# Override this function in order to change the default facet titles
# All of the imports above are coppied from ckan's group.py
class KWHOrganizationController(OrganizationController):

            
    def _read(self, id, limit, group_type):
            ''' This is common code used by both read and bulk_process'''
            context = {'model': model, 'session': model.Session,
                    'user': c.user,
                    'schema': self._db_to_form_schema(group_type=group_type),
                    'for_view': True, 'extras_as_string': True}

            q = c.q = request.params.get('q', '')
            # Search within group
            if c.group_dict.get('is_organization'):
                fq = 'owner_org:"%s"' % c.group_dict.get('id')
            else:
                fq = 'groups:"%s"' % c.group_dict.get('name')

            c.description_formatted = \
                h.render_markdown(c.group_dict.get('description'))

            context['return_query'] = True

            page = h.get_page_number(request.params)

            # most search operations should reset the page counter:
            params_nopage = [(k, v) for k, v in request.params.items()
                            if k != 'page']
            sort_by = request.params.get('sort', None)

            def search_url(params):
                controller = lookup_group_controller(group_type)
                action = 'bulk_process' if c.action == 'bulk_process' else 'read'
                url = h.url_for(controller=controller, action=action, id=id)
                params = [(k, v.encode('utf-8') if isinstance(v, string_types)
                        else str(v)) for k, v in params]
                return url + u'?' + urlencode(params)

            def drill_down_url(**by):
                return h.add_url_param(alternative_url=None,
                                    controller='group', action='read',
                                    extras=dict(id=c.group_dict.get('name')),
                                    new_params=by)

            c.drill_down_url = drill_down_url

            def remove_field(key, value=None, replace=None):
                controller = lookup_group_controller(group_type)
                return h.remove_url_param(key, value=value, replace=replace,
                                        controller=controller, action='read',
                                        extras=dict(id=c.group_dict.get('name')))

            c.remove_field = remove_field

            def pager_url(q=None, page=None):
                params = list(params_nopage)
                params.append(('page', page))
                return search_url(params)

            try:
                c.fields = []
                c.fields_grouped = {}
                search_extras = {}
                for (param, value) in request.params.items():
                    if param not in ['q', 'page', 'sort'] \
                            and len(value) and not param.startswith('_'):
                        if not param.startswith('ext_'):
                            c.fields.append((param, value))
                            q += ' %s: "%s"' % (param, value)
                            if param not in c.fields_grouped:
                                c.fields_grouped[param] = [value]
                            else:
                                c.fields_grouped[param].append(value)
                        else:
                            search_extras[param] = value

                facets = OrderedDict()

                default_facet_titles = {'organization': _('Functional Unit'),
                                        'groups': _('Joint Analysis'),
                                        'tags': _('Tags'),
                                        'res_format': _('Formats'),
                                        'license_id': _('Licenses')}

                for facet in h.facets():
                    if facet in default_facet_titles:
                        facets[facet] = default_facet_titles[facet]
                    else:
                        facets[facet] = facet

                # Facet titles
                self._update_facet_titles(facets, group_type)

                c.facet_titles = facets

                data_dict = {
                    'q': q,
                    'fq': fq,
                    'include_private': True,
                    'facet.field': facets.keys(),
                    'rows': limit,
                    'sort': sort_by,
                    'start': (page - 1) * limit,
                    'extras': search_extras
                }

                context_ = dict((k, v) for (k, v) in context.items()
                                if k != 'schema')
                query = get_action('package_search')(context_, data_dict)

                c.page = h.Page(
                    collection=query['results'],
                    page=page,
                    url=pager_url,
                    item_count=query['count'],
                    items_per_page=limit
                )

                c.group_dict['package_count'] = query['count']

                c.search_facets = query['search_facets']
                c.search_facets_limits = {}
                for facet in c.search_facets.keys():
                    limit = int(request.params.get('_%s_limit' % facet,
                                config.get('search.facets.default', 10)))
                    c.search_facets_limits[facet] = limit
                c.page.items = query['results']

                c.sort_by_selected = sort_by

            except search.SearchError as se:
                log.error('Group search error: %r', se.args)
                c.query_error = True
                c.page = h.Page(collection=[])

            self._setup_template_variables(context, {'id': id},
                                        group_type=group_type)


    def delete(self, id):
        group_type = self._ensure_controller_matches_group_type(id)

        if 'cancel' in request.params:
            h.redirect_to(group_type + '_edit', id=id)

        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        try:
            self._check_access('group_delete', context, {'id': id})
        except NotAuthorized:
            abort(403, _('Unauthorized to delete group. %s') % '')

        try:
            if request.method == 'POST':
                self._action('group_delete')(context, {'id': id})
                if group_type == 'organization':
                    h.flash_notice(_('Functional unit has been deleted.'))
                elif group_type == 'group':
                    h.flash_notice(_('Joint analysis has been deleted.'))
                else:
                    h.flash_notice(_('%s has been deleted.')
                                   % _(group_type.capitalize()))
                h.redirect_to(group_type + '_index')
            c.group_dict = self._action('group_show')(context, {'id': id})
        except NotAuthorized:
            abort(403, _('Unauthorized to delete group %s') % '')
        except NotFound:
            abort(404, _('Group not found'))
        except ValidationError as e:
            h.flash_error(e.error_dict['message'])
            h.redirect_to(controller='organization', action='read', id=id)
        return self._render_template('group/confirm_delete.html', group_type)
