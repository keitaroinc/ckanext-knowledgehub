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

from flask import Blueprint

import ckan.lib.base as base
import ckan.model as model
from ckan import authz
import ckan.logic as logic
import ckan.lib.helpers as h
from ckan.common import _, g, request, config
from flask.views import MethodView
import ckan.lib.navl.dictization_functions as dict_fns
from ckanext.knowledgehub.helpers import (
    check_user_profile_preferences,
    log_request
)
import ckanext.knowledgehub.views.access as access_requests
import ckanext.knowledgehub.views.request_audit as request_audit

kwh_user = Blueprint(
    u'kwh_user',
    __name__,
    url_prefix=u'/user'
)

# Handles the requests to /dashboard/posts - user's own news posts
user_dashboard = Blueprint(
    u'user_dashboard',
    __name__,
    url_prefix='/dashboard'
)


def _extra_template_variables(context, data_dict):
    is_sysadmin = authz.is_sysadmin(g.user)
    try:
        user_dict = logic.get_action(u'user_show')(context, data_dict)
    except logic.NotFound:
        h.flash_error(_(u'Not authorized to see this page'))
        return
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    is_myself = user_dict[u'name'] == g.user
    about_formatted = h.render_markdown(user_dict[u'about'])
    extra = {
        u'is_sysadmin': is_sysadmin,
        u'user_dict': user_dict,
        u'is_myself': is_myself,
        u'about_formatted': about_formatted
    }
    return extra


def intents(id):
    u'''Render intents page.'''

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    data_dict = {
        u'id': id,
        u'user_obj': g.userobj,
        u'include_num_followers': True
    }
    try:
        logic.check_access(u'intent_list', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    extra_vars = _extra_template_variables(context, data_dict)

    intent_dict = logic.get_action(u'user_intent_list')(context, {})
    extra_vars['intents'] = intent_dict['items']
    extra_vars['total'] = intent_dict['total']
    extra_vars['page'] = intent_dict['page']

    return base.render(u'user/intents.html', extra_vars)


def keywords():
    u'''Render the keywords list page
    '''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    data_dict = {
        u'user_obj': g.userobj,
        u'include_num_followers': True
    }
    try:
        logic.check_access(u'keyword_list', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    extra_vars = _extra_template_variables(context, data_dict)

    result = logic.get_action('keyword_list')(context, data_dict)
    extra_vars['keywords'] = result
    extra_vars['total'] = len(result)

    return base.render(u'user/keywords/keywords_list.html', extra_vars)


def keyword_create_update(show, create, id=None, data_dict=None):
    u'''Render the keyword update and create page and handle the POST
    requests to create new or update an existing keyword.
    '''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    user_page_data = {
        u'user_obj': g.userobj,
        u'include_num_followers': True
    }

    if not _check_action_access(context, 'keyword_show',
                                         'keyword_create',
                                         'keyword_update'):
        return

    data_dict = logic.clean_dict(
        dict_fns.unflatten(logic.tuplize_dict(
            logic.parse_params(request.form)
        ))
    )

    errors = {}
    if not show:
        if not data_dict.get('name'):
            errors['name'] = [_('Missing Value')]
        if not data_dict.get('tags'):
            errors['tags'] = [_('Missing Value')]

    keyword = {}
    if not errors:
        # If there are not validation errors, try to create/update the keyword

        if show:
            # We're populating the data to render on the create/update page
            if not create:
                keyword = logic.get_action('keyword_show')(context, {
                    'id': id,
                })
        else:
            # Handle the keyword update
            if create:
                keyword = {}
                keyword.update(data_dict)
            else:
                keyword = logic.get_action('keyword_show')(context, {
                    'id': id,
                })

            keyword['tags'] = data_dict.get('tags', '')
            try:
                keyword['name'] = data_dict['name']
                keyword = _save_keyword(context, keyword)
            except logic.ValidationError as e:
                keyword = data_dict
                errors.update(e.error_dict)

    else:
        # There were errors, so just return the dict
        keyword = data_dict

    extra_vars = _extra_template_variables(context, user_page_data)

    if (isinstance(keyword.get('tags'), str) or isinstance(keyword.get('tags'),
                                                           unicode)):
        keyword['tags'] = [{
            'name': tag.strip()
        } for tag in keyword.get('tags', '').split(',')]

    kwd_tags = []
    for tag in keyword.get('tags', []):
        kwd_tags.append(tag.get('name'))

    kwd_data = {
        'name': keyword.get('name'),
        'id': keyword.get('id'),
        'tags': ','.join(kwd_tags),
    }
    extra_vars['data'] = kwd_data
    extra_vars['errors'] = errors
    if show:
        return base.render('user/keywords/keyword_edit.html', extra_vars)
    else:
        if errors:
            return base.render('user/keywords/keyword_edit.html', extra_vars)
        return h.redirect_to('/user/keywords')


def _save_keyword(context, keyword_dict):
    update = False
    tags_list = filter(lambda t: t.strip(),
                       keyword_dict.get('tags', '').split(','))
    try:
        keyword = logic.get_action('keyword_show')(context, {
            'id': keyword_dict.get('id') or keyword_dict.get('name'),
        })
        update = True
    except logic.NotFound:
        keyword = logic.get_action('keyword_create')(context, {
            'name': keyword_dict['name'],
            'tags': tags_list,
        })

    if update:
        keyword = logic.get_action('keyword_update')(context, {
            'id': keyword['id'],
            'name': keyword_dict['name'],
            'tags': tags_list,
        })

    return logic.get_action('keyword_show')(context, {
        'id': keyword['id'],
    })


def _check_action_access(context, *args):
    try:
        for action in args:
            logic.check_access(action, context)
    except logic.NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))
        return False
    return True


def keyword_create_read():
    u'''Render the page for creating new keyword.
    '''
    return keyword_create_update(True, True)


def keyword_create_save():
    u'''Handle the save action to create new keyword.
    '''
    return keyword_create_update(False, True)


def keyword_update_read(id):
    u'''Render the page for updating an exitsting keyword.
    '''
    return keyword_create_update(True, False, id)


def keyword_update_save(id):
    u'''Handle the update of an existing keyword.
    '''
    return keyword_create_update(False, False, id)


def keyword_read(id):
    u'''Render the pagethat displayes the data for a particular keyword.
    '''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    user_page_data = {
        u'user_obj': g.userobj,
        u'include_num_followers': True
    }

    try:
        logic.check_access(u'keyword_show', context, {
            'id': id,
        })
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    try:
        keyword = logic.get_action('keyword_show')(context, {'id': id})
    except logic.NotFound:
        base.abort(404, _('Keyword not found'))

    extra_vars = _extra_template_variables(context, user_page_data)

    extra_vars['data'] = keyword
    extra_vars['errors'] = {}

    return base.render('user/keywords/keyword_read.html', extra_vars)


def keyword_delete(id):
    u'''Handle the keyword deletion.
    '''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    try:
        logic.check_access(u'keyword_delete', context, {
            'id': id,
        })
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    try:
        keyword = logic.get_action('keyword_show')(context, {'id': id})
    except logic.NotFound:
        base.abort(404, _('Keyword not found'))
    try:
        logic.get_action('keyword_delete')(context, {
            'id': id,
        })
    except Exception as e:
        base.abort(500, _('Server error'))

    return h.redirect_to('/user/keywords')


def tags(id):
    ''' Render tags page'''

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    data_dict = {
        u'id': id,
        u'user_obj': g.userobj,
        u'include_num_followers': True
    }
    try:
        logic.check_access(u'tag_list', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    extra_vars = _extra_template_variables(context, data_dict)

    tags = logic.get_action(u'tag_list')(context, {'all_fields': True})
    extra_vars['tags'] = tags
    extra_vars['total'] = len(tags)

    return base.render(u'user/tags.html', extra_vars)


def profile():
    u'''Renders the User Profile Interests page.
    '''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    data_dict = {
        u'user_obj': g.userobj,
        u'include_num_followers': True
    }
    try:
        logic.check_access(u'user_profile_show', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    extra_vars = _extra_template_variables(context, data_dict)
    return base.render('user/profile/user_profile.html', extra_vars)


def profile_set_interests():
    u'''Renders the page to set the user profile interests.
    '''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    data_dict = {
        u'user_obj': g.userobj,
        u'include_num_followers': True
    }
    try:
        logic.check_access(u'user_profile_show', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    logic.get_action('user_profile_update')(context, {
        'user_notified': True,
    })

    extra_vars = _extra_template_variables(context, data_dict)

    return base.render('user/profile/set_interests_page.html', extra_vars)


def user_posts():
    default_limit = int(config.get('ckanext.knowledgehub.news_per_page', '20'))
    page = request.args.get('page', '').strip()
    limit = request.args.get('limit', '').strip()
    partial = request.args.get('partial', 'false').lower()

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

    partial = partial in ['true', 'yes', '1', 't']
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    extra_vars = _extra_template_variables(context, {
        'user_obj': g.userobj,
        'user': g.userobj,
    })

    posts = logic.get_action('post_search')(context, {
        'text': '*',
        'fq': [
            'khe_created_by:"{}"'.format(g.userobj.id),
        ],
        'page': page,
        'limit': limit,
        'sort': 'created_at desc',
    })

    extra_vars['posts'] = posts.get('results', [])
    extra_vars['page'] = {
        'page': page,
        'items_per_page': limit,
        'item_count': posts.get('count'),
    }

    if partial:
        return base.render(u'news/snippets/post_list.html',
                           extra_vars=extra_vars)

    return base.render(u'user/dashboard_posts.html', extra_vars=extra_vars)


kwh_user.add_url_rule(u'/intents/<id>', view_func=intents)
kwh_user.add_url_rule(u'/keywords', view_func=keywords)
kwh_user.add_url_rule(u'/keywords/delete/<id>', methods=['GET', 'POST'],
                      view_func=keyword_delete)
kwh_user.add_url_rule(u'/keywords/edit/<id>', methods=['GET'],
                      view_func=keyword_update_read)
kwh_user.add_url_rule(u'/keywords/edit/<id>', methods=['POST'],
                      view_func=keyword_update_save)
kwh_user.add_url_rule(u'/keywords/new', methods=['GET'],
                      view_func=keyword_create_read)
kwh_user.add_url_rule(u'/keywords/new', methods=['POST'],
                      view_func=keyword_create_save)
kwh_user.add_url_rule(u'/keywords/<id>', view_func=keyword_read)
kwh_user.add_url_rule(u'/tags/<id>', view_func=tags)
kwh_user.add_url_rule(u'/profile', view_func=profile)
kwh_user.add_url_rule(u'/profile/set_interests',
                      view_func=profile_set_interests)
user_dashboard.add_url_rule(u'/posts', view_func=user_posts,
                            strict_slashes=False)


# Register the rules for Access requests
access_requests.register_url_rules(user_dashboard)
request_audit.register_url_rules(user_dashboard)


@kwh_user.before_app_request
def check_user_prefrences():
    log_request()
    return check_user_profile_preferences()
