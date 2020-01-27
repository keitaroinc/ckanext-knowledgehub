import logging
import os

from flask import Blueprint, request
from flask.views import MethodView

from werkzeug.datastructures import FileStorage as FlaskFileStorage

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.uploader as uploader
import ckan.logic as logic
import ckan.model as model
from ckan.common import g, _, request, config
from ckan.lib.navl import dictization_functions
import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)


NotFound = logic.NotFound
NotAuthorized = toolkit.NotAuthorized
ValidationError = toolkit.ValidationError
check_access = toolkit.check_access
get_action = toolkit.get_action
abort = toolkit.abort
render = toolkit.render

new_research_question_form = \
    u'research_question/new_research_question_form.html'
edit_sub_theme_form = \
    u'research_question/edit_research_question_form.html'

ALLOWED_IMAGE_EXTENSIONS = [
    "ase", "art", "bmp", "blp", "cd5", "cit", "cpt", "cr2", "cut",
    "dds", "dib", "djvu", "egt", "exif", "gif", "gpl", "grf", "icns",
    "ico", "iff", "jng", "jpeg", "jpg", "JPG", "jfif", "jp2", "jps", "lbm",
    "max", "miff", "mng", "msp", "nitf", "ota", "pbm", "pc1", "pc2",
    "pc3", "pcf", "pcx", "pdn", "pgm", "PI1", "PI2", "PI3", "pict",
    "pct", "pnm", "pns", "ppm", "psb", "psd", "pdd", "psp", "px",
    "pxm", "pxr", "qfx", "raw", "rle", "sct", "sgi", "rgb", "int",
    "bw", "tga", "tiff", "tif", "vtf", "xbm", "xcf", "xpm", "3dv",
    "amf", "ai", "awg", "cgm", "cdr", "cmx", "dxf", "e2d", "egt",
    "eps", "fs", "gbr", "odg", "svg", "stl", "vrml", "x3d", "sxd",
    "v2d", "vnd", "wmf", "emf", "art", "xar", "png", "webp", "jxr",
    "hdp", "wdp", "cur", "ecw", "iff", "lbm", "liff", "nrrd", "pam",
    "pcx", "pgf", "sgi", "rgb", "rgba", "bw", "int", "inta", "sid",
    "ras", "sun", "tga"
]


research_question = Blueprint(
    u'research_question',
    __name__,
    url_prefix=u'/research-question'
)


def _get_context():
    return dict(model=model, user=g.user,
                auth_user_obj=g.userobj,
                session=model.Session)


def _get_question_themes(context, research_question):

    def _call_action_safe(action, context, data_dict):
        try:
            return get_action(action)(context, data_dict)
        except Exception as e:
            log.debug('Failed to call action %s. Error: %s', action, e)
        return None

    if research_question.get('theme'):
        theme = _call_action_safe('theme_show',
                                  context,
                                  {'id': research_question['theme']})
        if theme:
            research_question['theme_data'] = theme

    if research_question.get('sub_theme'):
        sub_theme = _call_action_safe('sub_theme_show',
                                      context,
                                      {'id': research_question['sub_theme']})
        if sub_theme:
            research_question['sub_theme_data'] = sub_theme

    return research_question


def search():

    q = request.params.get(u'q', u'')
    page = request.params.get(u'page', 1)
    order_by = request.params.get(u'sort', u'name asc')
    limit = int(request.params.get(u'limit', config.get(
        u'ckanext.knowledgehub.research_question_limit', 10)))

    data_dict = {
        u'q': q,
        u'order_by': order_by,
        u'pageSize': limit,
        u'page': page
    }

    try:
        research_question_list = get_action(
            u'research_question_list')({}, data_dict)
    except NotAuthorized:
        abort(403)

    page = h.Page(
        collection=research_question_list.get(u'data', []),
        page=page,
        url=h.pager_url,
        item_count=research_question_list.get(u'total', 0),
        items_per_page=limit)

    extra_vars = {
        u'total': research_question_list.get('total', 0),
        u'research_questions': research_question_list.get('data', []),
        u'q': q,
        u'order_by': order_by,
        u'page': page
    }

    return render(u'research_question/search.html',
                  extra_vars=extra_vars)


def read(name):

    data_dict = {'name': name}

    context = _get_context()
    try:
        rq = get_action(
            u'research_question_show')(context, data_dict)
        rq = _get_question_themes(context, rq)
    except (NotFound, NotAuthorized):
        abort(404, _(u'Research question not found'))

    extra_vars = {
        'rq': rq,
        'image_url': rq.get('image_url')
    }

    return render(u'research_question/read.html',
                  extra_vars=extra_vars)


def delete(id):

    context = _get_context()
    try:
        check_access(u'research_question_delete', context)
    except NotAuthorized:
        return base.abort(403, _(u'Unauthorized'
                                 u' to delete a research'
                                 u' question'))

    data_dict = {u'id': id}

    try:
        get_action(u'research_question_delete')(context, data_dict)
    except NotAuthorized:
        abort(403, _(u'Unauthorized to delete this research question'))

    return h.redirect_to('research_question.search')


class CreateView(MethodView):

    def _is_save(self):
        return u'save' in request.form

    def _prepare(self, data=None):

        context = _get_context()
        try:
            check_access(u'research_question_create', context)
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized'
                                     u' to create a '
                                     u'research question'))
        return context

    def get(self, data=None, errors=None, error_summary=None):

        context = self._prepare()
        data = data or {}
        theme_selected = data.get('theme', None)

        theme_options = []
        theme_list = get_action(u'theme_list')(context, {})
        for theme in theme_list.get(u'data', []):
            opt = {u'text': theme[u'title'], u'value': theme[u'id']}
            theme_options.append(opt)

        sub_theme_options = []

        if theme_selected:
            sub_theme_list = get_action(u'sub_theme_list')(
                context, {'theme': theme_selected})

            for sub_theme in sub_theme_list.get(u'data', []):
                opt = {u'text': sub_theme[u'title'],
                       u'value': sub_theme[u'id']}
                sub_theme_options.append(opt)

        theme_options.insert(0, {'text': 'Select theme', 'value': ''})
        sub_theme_options.insert(0, {'text': 'Select sub-theme', 'value': ''})

        image = data.get('image_url', '')
        if not (image.startswith('http') or image.startswith('https')):
            data['image_url'] = image.split('/')[-1]

        form_vars = {
            u'data': data,
            u'theme': data.get('theme'),
            u'sub_theme': data.get('sub_theme'),
            u'theme_options': theme_options,
            u'sub_theme_options': sub_theme_options,
            u'errors': errors or {},
            u'error_summary': error_summary or {}
        }

        extra_vars = {
            u'form': render(new_research_question_form, form_vars)
        }

        return render(u'research_question/new.html', extra_vars)

    def post(self):

        context = self._prepare()
        try:
            data_dict = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(
                            request.form
                        )
                    )
                )
            )
        except dictization_functions.DataError:
            abort(400, _(u'Integrity Error'))

        if 'upload' in request.files:
            if h.uploads_enabled():
                image_upload = request.files.get('upload')
                image_url = data_dict.get('image_url')
                image_ext = os.path.splitext(image_url)[1][1:]
                if image_ext not in ALLOWED_IMAGE_EXTENSIONS:
                    errors = {
                        'url': ['Image extension not allowed!'],
                    }
                    error_summary = {
                        'url': 'Image extension not allowed!',
                    }
                    return self.get(data_dict, errors, error_summary)

                data_dict['upload'] = image_upload
                if isinstance(image_upload, FlaskFileStorage):
                    try:
                        upload = uploader.get_uploader(
                            'research_questions', image_url)
                        upload.update_data_dict(data_dict,
                                                'url',
                                                'upload',
                                                'False')
                        upload.upload()
                        data_dict['image_url'] = h.url_for_static(
                            'uploads/research_questions/%s' % upload.filename)
                    except ValidationError as e:
                        errors = e.error_dict
                        error_summary = e.error_summary
                        return self.get(data_dict, errors, error_summary)

        if not data_dict.get('image_url'):
            data_dict['image_url'] = h.url_for_static(
                '/base/images/placeholder-rq.png')

        try:
            research_question = logic.get_action(
                u'research_question_create')(context, data_dict)
        except NotAuthorized:
            abort(403)
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(data_dict, errors, error_summary)

        try:
            kwh_data = {
                'type': 'rq',
                'content': research_question.get('title'),
                'rq': research_question.get('id')
            }
            logic.get_action(u'kwh_data_create')(
                context, kwh_data
            )
        except Exception as e:
            log.debug('Error while storing KWH data: %s' % str(e))

        return h.redirect_to(
            u'research_question.read',
            name=research_question.get(u'name'))


class EditView(MethodView):

    def _is_save(self):
        return u'save' in request.form

    def _prepare(self, name=None):

        context = _get_context()
        try:
            research_question = logic.get_action(
                u'research_question_show')({}, {'name': name})
        except logic.NotFound:
            base.abort(404, _(u'Research question not found'))

        research_question = _get_question_themes(context, research_question)
        context['research_question'] = research_question

        try:
            logic.check_access(u'research_question_update', context)
        except logic.NotAuthorized:
            return base.abort(403, _(
                u'Unauthorized to edit research question'))

        return context

    def get(self, name=None, data=None,
            errors=None,
            error_summary=None):

        context = self._prepare(name)
        research_question = context['research_question']
        new_theme_selected = request.params.get('theme', None)

        theme_options = []
        theme_list = get_action(u'theme_list')(context, {})
        for theme_item in theme_list.get(u'data', []):
            opt = {u'text': theme_item[u'title'], u'value': theme_item[u'id']}
            theme_options.append(opt)

        sub_theme_options = []

        if new_theme_selected:
            theme = new_theme_selected
        elif research_question['theme']:
            theme = research_question['theme']
        else:
            theme = None

        if theme:
            sub_theme_list = get_action(u'sub_theme_list')(
                context, {'theme': theme})

            for sub_theme in sub_theme_list.get(u'data', []):
                opt = {u'text': sub_theme[u'title'],
                       u'value': sub_theme[u'id']}
                sub_theme_options.append(opt)

        theme_options.insert(0, {'text': 'Select theme', 'value': ''})
        sub_theme_options.insert(0, {'text': 'Select sub-theme', 'value': ''})

        data = data or research_question

        if data:
            image = data.get('image_url') or ''
            if not (image.startswith('http') or
                    image.startswith('https')):
                data['image_url'] = image.split('/')[-1]

        form_vars = {
            u'id': research_question.get('id', ''),
            u'user': context.get('user'),
            u'data': data,
            u'theme': research_question.get('theme', ''),
            u'theme_options': theme_options,
            u'sub_theme': research_question.get('sub_theme', ''),
            u'sub_theme_options': sub_theme_options,
            u'errors': errors or {},
            u'error_summary': error_summary or {}
        }

        return render(
            u'research_question/edit.html',
            extra_vars={
                u'rq': research_question,
                u'form': render(edit_sub_theme_form, form_vars)
            }
        )

    def post(self, name=None):

        context = self._prepare(name)
        research_question = context['research_question']

        try:
            data_dict = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(request.form))))
        except dictization_functions.DataError:
            abort(400, _(u'Integrity Error'))

        data_dict['id'] = research_question.get('id')
        data_dict.pop('save', '')

        if 'upload' in request.files:
            if h.uploads_enabled():
                image_upload = request.files.get('upload')
                image_url = data_dict.get('image_url')
                image_ext = os.path.splitext(image_url)[1][1:]
                if image_ext not in ALLOWED_IMAGE_EXTENSIONS:
                    errors = {
                        'url': ['Image extension not allowed!'],
                    }
                    error_summary = {
                        'url': 'Image extension not allowed!',
                    }
                    return self.get(data_dict, errors, error_summary)

                data_dict['upload'] = image_upload
                if isinstance(image_upload, FlaskFileStorage):
                    try:
                        upload = uploader.get_uploader(
                            'research_questions', image_url)
                        upload.update_data_dict(data_dict,
                                                'url',
                                                'upload',
                                                'False')
                        upload.upload()
                        data_dict['image_url'] = h.url_for_static(
                            'uploads/research_questions/%s' % upload.filename)
                    except ValidationError as e:
                        errors = e.error_dict
                        error_summary = e.error_summary
                        return self.get(data_dict, errors, error_summary)
        else:
            image_url = data_dict.get('image_url')
            if not image_url or image_url == 'placeholder-rq.png':
                data_dict['image_url'] = h.url_for_static(
                    '/base/images/placeholder-rq.png')
            elif not (image_url.startswith('http') or
                      image_url.startswith('https')):
                data_dict['image_url'] = h.url_for_static(
                    'uploads/research_questions/%s' % image_url)

        try:
            research_question = get_action(
                u'research_question_update')(context, data_dict)
        except NotAuthorized:
            abort(403, _(u'Unauthorized to update this research question'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(name, data_dict, errors, error_summary)

        try:
            old_rq = context['research_question']
            kwh_data = {
                'type': 'rq',
                'old_content': old_rq.get('title'),
                'new_content': research_question.get('title')
            }
            logic.get_action(u'kwh_data_update')(
                context, kwh_data
            )
        except Exception as e:
            log.debug('Error while storing KWH data: %s' % str(e))

        return h.redirect_to(u'research_question.read',
                             name=research_question.get(u'name'))


research_question.add_url_rule(u'/', view_func=search, strict_slashes=False)
research_question.add_url_rule(
    u'/new', view_func=CreateView.as_view(str(u'new')))
research_question.add_url_rule(
    u'/edit/<name>', view_func=EditView.as_view(str(u'edit')))
research_question.add_url_rule(u'/<name>', view_func=read)
research_question.add_url_rule(
    u'/delete/<id>', view_func=delete, methods=(u'POST', ))
