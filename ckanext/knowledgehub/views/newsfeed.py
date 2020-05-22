# encoding: utf-8
import logging

from flask import Blueprint
from flask.views import MethodView
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request, c
import ckanext.knowledgehub.helpers as kwh_helpers
import ckan.lib.navl.dictization_functions as dict_fns


log = logging.getLogger(__name__)

get_action = logic.get_action
check_access = logic.check_access
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params


newsfeed = Blueprint(
    u'news',
    __name__,
    url_prefix=u'/news'
)

_all_helpers = {}


def _get_context():
    return dict(model=model, user=g.user,
                auth_user_obj=g.userobj,
                session=model.Session)


def index():
    u'''List all news on the feed.
    '''
    context = _get_context()
    try:
        check_access('post_search', context, {})
    except logic.NotAuthorized:
        base.abort(403, _('Only logged in users can view news feed.'))
        return

    default_limit = int(config.get('ckanext.knowledgehub.news_per_page', '20'))
    text = request.args.get('q', '').strip()
    page = request.args.get('page', '').strip()
    limit = request.args.get('limit', '').strip()
    partial = request.args.get('partial', 'false').lower()
    post_types = request.args.getlist('khe_entity_type')
    fq = []

    if not text:
        text = '*'
    if not page:
        page = 1
    else:
        page = int(page)
        if page < 1:
            page = 1
    if limit:
        limit = int(limit)
        if limit < 0:
            limit = default_limit
    else:
        limit = default_limit

    for post_type in post_types:
        fq.append('khe_entity_type:"{}"'.format(post_type))

    partial = partial in ['true', 'yes', '1', 't']

    posts = get_action('post_search')(context, {
        'text': text,
        'page': page,
        'limit': limit,
        'sort': 'created_at desc',
        'facet': True,
        'facet.field': ['khe_entity_type'],
        'fq': fq,
    })

    extra_vars = {
        'posts': posts.get('results', []),
        'user': context.get('auth_user_obj'),
    }

    traslated_fields = {
        'dashboard': _('Dashboards'),
        'research_question': _('Research Questions'),
        'dataset': _('Datasets'),
        'visualization': _('Visualizations'),
    }

    search_facets = {}
    if posts.get('facets', {}).get('khe_entity_type'):
        facet_items = []
        search_facets['khe_entity_type'] = {'items': facet_items}
        for field, count in posts['facets']['khe_entity_type'].items():
            facet_items.append({
                'name': field,
                'display_name': traslated_fields.get(field, field),
                'count': count,
            })

    c.search_facets = search_facets
    c.search_facets_limits = {}
    for facet in c.search_facets.keys():
        limit = int(request.args.get('_%s_limit' % facet,
                    config.get('search.facets.default', 10)))
        c.search_facets_limits[facet] = limit

    def remove_field(field, value):
        query_params = []
        for argn in request.args:
            values = request.args.getlist(argn)
            for val in values:
                if field == argn and val == value:
                    continue
                query_params.append('{}={}'.format(argn, val))

        url = h.url_for('news.index')
        if query_params:
            return url + '?' + '&'.join(query_params)
        return url

    facets = {
        'search': search_facets,
        'remove_field': remove_field,
    }

    facets['titles'] = {'khe_entity_type': _('Post type')}
    fields_grouped = {}
    if post_types:
        facets['fields'] = {'khe_entity_type': post_types}

    for argn in request.args:
        if argn == 'q':
            continue
        values = request.args.getlist(argn)
        for value in values:
            fields_grouped[(argn, value)] = value

    facets['fields_grouped'] = fields_grouped

    extra_vars['facets'] = facets

    extra_vars["page"] = h.Page(
        collection=posts.get('results', []),
        page=page,
        url=h.pager_url,
        items_per_page=limit,
        item_count=posts.get('count'))

    extra_vars['page'].items = posts.get('results', [])

    if partial:
        return base.render(u'news/snippets/post_list.html',
                           extra_vars=extra_vars)

    return base.render(u'news/index.html',
                       extra_vars=extra_vars)


def view(id):
    '''View the post with the given ID.
    '''
    context = _get_context()

    post = None
    try:
        post = get_action('post_show')(context, {
            'id': id,
        })
    except logic.NotFound:
        base.abort(404, _('Post not found'))
        return
    except logic.NotAuthorized:
        base.abort(403, _('Not authorized to see this post'))
        return

    extra_vars = {
        'post': post,
        'user': context.get('auth_user_obj'),
        'facets': {},
    }

    extra_vars["page"] = h.Page(
        collection=[],
        page=1,
        url=h.pager_url,
        items_per_page=20,
        item_count=1)

    return base.render(u'news/view_post.html', extra_vars=extra_vars)


def delete(id):
    '''Delete the post with the given ID.
    '''
    context = _get_context()

    try:
        check_access('post_delete', context, {'id': id})
    except logic.NotAuthorized:
        base.abort(403, _('You do not have sufficient privileges '
                          'to delete this post.'))
        return

    try:
        get_action('post_delete')(context, {
            'id': id,
        })
    except logic.NotFound:
        base.abort(404, _('That post does not exist.'))
        return
    except logic.NotAuthorized:
        base.abort(403, _('You do not have sufficient privileges '
                          'to delete this post.'))
        return
    except Exception as e:
        log.error('Failed to delete post %s. Error: %s', id, str(e))
        log.exception(e)
        base.abort(500, _('Unexpected error has occured while trying '
                          'to delete this post.'))
        return
    return h.redirect_to(u'news.index')


class CreateView(MethodView):

    def _get_entity(self, context, entity_type, entity_ref):
        actions = {
            'dashboard': 'dashboard_show',
            'research_question': 'research_question_show',
            'dataset': 'package_show',
            'visualization': 'resource_view_show',
        }
        return get_action(actions[entity_type])(context, {
            'id': entity_ref,
        })

    def get(self):
        context = _get_context()
        try:
            check_access('post_create', context)
        except logic.NotAuthorized:
            base.abort(403, _('Not authorized to create a news feed post.'))
            return

        entity_type = request.args.get('entity_type', '')
        entity_ref = request.args.get('entity_ref', '')
        data = {
            'entity_type': entity_type,
            'entity_ref': entity_ref,
        }
        errors = {}

        if entity_type and entity_ref:
            try:
                data[entity_type] = self._get_entity(context,
                                                     entity_type,
                                                     entity_ref)
            except logic.NotFound:
                errors['entity'] = _('Cannot find {} to preview.').format(
                    entity_type)
            except logic.NotAuthorized:
                base.abort(403, _('You are not authorized to access '
                                  'this resource'))
            except Exception as e:
                errors['entity'] = _('Unexpected error: {}').format(str(e))
                log.error('Failed to load preview for %s with id %s',
                          entity_type,
                          entity_ref)
                log.exception(e)

        return base.render(u'news/create_post.html', {
            'data': data,
            'errors': errors,
            'page': {},
            'facets': {},
        })

    def post(self):
        context = _get_context()
        try:
            check_access('post_create', context)
        except logic.NotAuthorized:
            base.abort(403, _('Not authorized to create a news feed post.'))
            return
        data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(
                    parse_params(request.form)
                ))
            )

        title = data_dict.get('title', '').strip()
        description = data_dict.get('description', '').strip()
        entity_type = data_dict.get('entity_type', '').strip()
        entity_ref = data_dict.get('entity_ref', '').strip()

        errors = {}
        if not title:
            errors['title'] = [_('Missing value')]
        if entity_type and not entity_ref:
            errors['entity_ref'] = [_('Missing value')]

        data = {
            'title': title,
            'description': description,
            'entity_type': entity_type,
            'entity_ref': entity_ref,
        }

        if entity_type and entity_ref:
            try:
                data[entity_type] = self._get_entity(context,
                                                     entity_type,
                                                     entity_ref)
            except logic.NotFound:
                errors['entity'] = [_('Cannot find {} to preview.').format(
                    entity_type)]
            except logic.NotAuthorized:
                base.abort(403, _('You are not authorized to access '
                                  'this resource'))
            except Exception as e:
                errors['entity'] = [_('Unexpected error: {}').format(str(e))]
                log.error('Failed to load preview for %s with id %s',
                          entity_type,
                          entity_ref)
                log.exception(e)

        if errors:
            return base.render(u'news/create_post.html', {
                'data': data,
                'errors': errors,
                'page': {},
                'facets': {},
            })

        try:
            get_action('post_create')(context, data)
        except logic.NotAuthorized:
            base.abort(403, _('You are not authorized to create a post.'))
            return
        except logic.NotFound:
            errors['entity'] = [_('The referenced data in the post '
                                  'was not found.')]
        except Exception as e:
            log.error('Failed to create post. Error: %s', str(e))
            log.exception(e)
            base.abort(500, _('An unexpected error has happened.'))
            return

        if errors:
            return base.render(u'news/create_post.html', {
                'data': data,
                'errors': errors,
                'page': {},
                'facets': {},
            })

        return h.redirect_to(u'news.index')


newsfeed.add_url_rule(u'/', view_func=index, strict_slashes=False)
newsfeed.add_url_rule(u'/new', view_func=CreateView.as_view('new'))
newsfeed.add_url_rule(u'/<id>', view_func=view)
newsfeed.add_url_rule(u'/delete/<id>', view_func=delete, methods=['POST'])
