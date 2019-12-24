from flask import Blueprint

import ckan.lib.base as base
import ckan.model as model
from ckan import authz
import ckan.logic as logic
import ckan.lib.helpers as h
from ckan.common import _, g


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

    intent_dict = logic.get_action(u'user_intent_list')(context, data_dict)
    extra_vars['intents'] = intent_dict['items']
    extra_vars['total'] = intent_dict['total']
    extra_vars['page'] = intent_dict['page']

    return base.render(u'user/intents.html', extra_vars)


kwh_user.add_url_rule(u'/intents/<id>', view_func=intents)
