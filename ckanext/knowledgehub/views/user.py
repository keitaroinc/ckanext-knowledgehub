from flask import Blueprint

import ckan.lib.base as base
import ckan.model as model
from ckan import authz
import ckan.logic as logic
import ckan.lib.helpers as h
from ckan.common import _, g, request
from flask.views import MethodView
import ckan.lib.navl.dictization_functions as dict_fns


kwh_user = Blueprint(
    u'kwh_user',
    __name__,
    url_prefix=u'/user'
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
        logic.check_access(u'vocabulary_list', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    extra_vars = _extra_template_variables(context, data_dict)

    result = logic.get_action('vocabulary_list')(context, data_dict)
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

    if not _check_action_access(context, 'vocabulary_show',
                                         'vocabulary_create',
                                         'vocabulary_update'):
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
                keyword = logic.get_action('vocabulary_show')(context, {
                    'id': id,
                })
        else:
            # Handle the keyword update
            if create:
                keyword = {}
                keyword.update(data_dict)
            else:
                keyword = logic.get_action('vocabulary_show')(context, {
                    'id': id,
                })

            keyword['tags'] = [{
                'name': tag.strip(),
            } for tag in data_dict.get('tags', '').split(',')]

            keyword = _save_keyword(context, keyword)

    else:
        # There were errors, so just return the dict
        keyword = data_dict

    extra_vars = _extra_template_variables(context, user_page_data)

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
    if keyword_dict.get('id'):
        keyword = logic.get_action('vocabulary_show')(context, {
            'id': keyword_dict.get('id'),
        })
        update = True
    else:
        keyword = logic.get_action('vocabulary_create')(context, {
            'name': keyword_dict['name'],
            'tags': [],
        })
    for tag in keyword.get('tags', []):
        logic.get_action('tag_update')(context, {
            'id': tag.get('id'),
            'name': tag.get('name'),
            'vocabulary_id': None,  # delete the FK to vocabulary
        })

    if update:
        keyword = logic.get_action('vocabulary_update')(context, {
            'id': keyword['id'],
            'name': keyword['name'],
            'tags': [],
        })

    for tag in keyword_dict.get('tags', []):
        try:
            tag = logic.get_action('tag_show')(context, {'id': tag['name']})
        except logic.NotFound:
            tag = logic.get_action('tag_create')(context, {
                'name': tag['name'],
                'display_name': tag['name'],
            })

        logic.get_action('tag_update')(context, {
            'id': tag['id'],
            'vocabulary_id': keyword['id'],
        })

    return logic.get_action('vocabulary_show')(context, {
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
        logic.check_access(u'vocabulary_show', context, {
            'id': id,
        })
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    try:
        keyword = logic.get_action('vocabulary_show')(context, {'id': id})
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
        logic.check_access(u'vocabulary_delete', context, {
            'id': id,
        })
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    try:
        keyword = logic.get_action('vocabulary_show')(context, {'id': id})
    except logic.NotFound:
        base.abort(404, _('Keyword not found'))
    try:
        logic.get_action('vocabulary_delete')(context, {
            'id': id,
        })
    except:
        base.abort(500, _('Server error'))

    return h.redirect_to('/user/keywords')


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
