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
    text = request.args.get('q', '').strip()
    page = request.args.get('page', '').strip()
    limit = request.args.get('limit', '').strip()
    partial = request.args.get('partial', 'false').lower()

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
            limit = 20
    else:
        limit = 20

    partial = partial in ['true', 'yes', '1', 't']

    posts = get_action('post_search')(context, {
        'text': text,
        'page': page,
        'limit': limit,
        'sort': 'created_at desc'
    })

    extra_vars = {
        'posts': posts.get('results', []),
    }

    extra_vars["page"] = h.Page(
        collection=posts.get('results', []),
        page=1,
        url=h.pager_url,
        items_per_page=20)

    extra_vars['page'].items = posts.get('results', [])

    if partial:
        return base.render(u'news/snippets/post_list.html',
                           extra_vars=extra_vars)

    return base.render(u'news/index.html',
                       extra_vars=extra_vars)


def view(id):

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
    }

    extra_vars["page"] = h.Page(
        collection=[],
        page=1,
        url=h.pager_url,
        items_per_page=20)

    return base.render(u'news/view_post.html', extra_vars=extra_vars)


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
            })

        return h.redirect_to(u'news.index')


newsfeed.add_url_rule(u'/', view_func=index, strict_slashes=False)
newsfeed.add_url_rule(u'/new', view_func=CreateView.as_view('new'))
newsfeed.add_url_rule(u'/<id>', view_func=view)
