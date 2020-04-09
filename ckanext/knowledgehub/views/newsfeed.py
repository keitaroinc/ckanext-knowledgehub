# encoding: utf-8
import logging

from flask import Blueprint

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model


newsfeed = Blueprint(
    u'news',
    __name__,
    url_prefix=u'/news'
)


def _get_context():
    return dict(model=model, user=g.user,
                auth_user_obj=g.userobj,
                session=model.Session)


def index():
    u'''List all news on the feed.
    '''

    extra_vars = {}

    extra_vars["page"] = h.Page(
        collection=[],
        page=1,
        url=h.pager_url,
        items_per_page=20)

    extra_vars['page'].items = []

    return base.render(u'news/index.html',
                       extra_vars=extra_vars)


newsfeed.add_url_rule(u'/', view_func=index, strict_slashes=False)
