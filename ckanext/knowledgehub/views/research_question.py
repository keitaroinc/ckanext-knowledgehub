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

new_research_question_form = u'research_question/new_research_question_form.html'
edit_sub_theme_form = u'research_question/edit_research_question_form.html'

ALLOWED_IMAGE_EXTENSIONS = [
	"ase",
	"art",
	"bmp",
	"blp",
	"cd5",
	"cit",
	"cpt",
	"cr2",
	"cut",
	"dds",
	"dib",
	"djvu",
	"egt",
	"exif",
	"gif",
	"gpl",
	"grf",
	"icns",
	"ico",
	"iff",
	"jng",
	"jpeg",
	"jpg",
	"jfif",
	"jp2",
	"jps",
	"lbm",
	"max",
	"miff",
	"mng",
	"msp",
	"nitf",
	"ota",
	"pbm",
	"pc1",
	"pc2",
	"pc3",
	"pcf",
	"pcx",
	"pdn",
	"pgm",
	"PI1",
	"PI2",
	"PI3",
	"pict",
	"pct",
	"pnm",
	"pns",
	"ppm",
	"psb",
	"psd",
	"pdd",
	"psp",
	"px",
	"pxm",
	"pxr",
	"qfx",
	"raw",
	"rle",
	"sct",
	"sgi",
	"rgb",
	"int",
	"bw",
	"tga",
	"tiff",
	"tif",
	"vtf",
	"xbm",
	"xcf",
	"xpm",
	"3dv",
	"amf",
	"ai",
	"awg",
	"cgm",
	"cdr",
	"cmx",
	"dxf",
	"e2d",
	"egt",
	"eps",
	"fs",
	"gbr",
	"odg",
	"svg",
	"stl",
	"vrml",
	"x3d",
	"sxd",
	"v2d",
	"vnd",
	"wmf",
	"emf",
	"art",
	"xar",
	"png",
	"webp",
	"jxr",
	"hdp",
	"wdp",
	"cur",
	"ecw",
	"iff",
	"lbm",
	"liff",
	"nrrd",
	"pam",
	"pcx",
	"pgf",
	"sgi",
	"rgb",
	"rgba",
	"bw",
	"int",
	"inta",
	"sid",
	"ras",
	"sun",
	"tga"
]


research_question = Blueprint(
    u'research_question',
    __name__,
    url_prefix=u'/research-question'
)


@research_question.before_request
def before_request():
    context = dict(model=model, user=g.user, auth_user_obj=g.userobj)


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

    return render(u'research_question/search.html',
                  extra_vars={
                      u'total': research_question_list.get('total', 0),
                      u'research_questions': research_question_list.get('data', []),
                      u'q': q,
                      u'order_by': order_by,
                      u'page': page
                  })


def read(name):
    data_dict = {'name': name}

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }

    try:
        rq = get_action(u'research_question_show')(context, data_dict)
    except (NotFound, NotAuthorized):
        abort(404, _(u'Research question not found'))

    extra_vars = {
        'rq': rq,
        'image_url': rq.get('image_url')
    }

    return render(u'research_question/read.html', extra_vars=extra_vars)


def delete(id):
    data_dict = {u'id': id}
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
    }

    try:
        get_action(u'research_question_delete')(context, data_dict)
    except NotAuthorized:
        abort(403, _(u'Unauthorized to delete this research question'))

    return h.redirect_to('research_question.search')


class CreateView(MethodView):

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
            ValidationError(u'research_question_create', context)
        except NotAuthorized:
            return abort(403)
        return context

    def get(self, data=None, errors=None, error_summary=None):
        context = self._prepare()
        data_dict = data or {}
        theme_selected = data_dict.get('theme', None)

        theme_options = []
        theme_list = get_action(u'theme_list')(context, {})
        for theme in theme_list.get(u'data', []):
            opt = {u'text': theme[u'title'], u'value': theme[u'id']}
            theme_options.append(opt)

        sub_theme_options = []

        if theme_selected:
            sub_theme_list = get_action(u'sub_theme_list')(context,
                                                           {'theme': theme_selected})

            for sub_theme in sub_theme_list.get(u'data', []):
                opt = {u'text': sub_theme[u'title'],
                       u'value': sub_theme[u'id']}
                sub_theme_options.append(opt)

        theme_options.insert(0, {'text': 'Select theme', 'value': ''})

        image = data_dict.get('image_url', '')
        if not (image.startswith('http') or image.startswith('https')):
            data_dict['image_url'] = image.split('/')[-1]

        form_vars = {
            u'data': data_dict,
            u'theme': data_dict.get('theme'),
            u'sub_theme': data_dict.get('sub_theme'),
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
                dictization_functions.unflatten(logic.tuplize_dict(logic.parse_params(request.form))))
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
                        upload = uploader.get_uploader('research_questions', image_url)
                        upload.update_data_dict(data_dict,
                                                'url',
                                                'upload',
                                                'False')
                        upload.upload()
                        data_dict['image_url'] = h.url_for_static('uploads/research_questions/%s' % upload.filename)
                    except ValidationError as e:
                        errors = e.error_dict
                        error_summary = e.error_summary
                        return self.get(data_dict, errors, error_summary)

        if not data_dict.get('image_url'):
            data_dict['image_url'] = h.url_for_static('/base/images/placeholder-rq.png')

        try:
            research_question = logic.get_action(
                u'research_question_create')(context, data_dict)
        except NotAuthorized:
            abort(403)
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(data_dict, errors, error_summary)

        return h.redirect_to(u'research_question.read', name=research_question.get(u'name'))


class EditView(MethodView):

    def _is_save(self):
        return u'save' in request.form

    def _prepare(self, name=None):

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj,
            u'save': self._is_save()
        }
        try:
            research_question = logic.get_action(u'research_question_show')({}, {'name': name})
        except logic.NotFound:
            base.abort(404, _(u'Research question not found'))

        context['research_question'] = research_question

        try:
            logic.check_access(u'research_question_update', context)
        except logic.NotAuthorized:
            return base.abort(403, _(u'Unauthorized to edit research question'))

        return context


    def get(self, name=None, data=None, errors=None, error_summary=None):
        context = self._prepare(name)
        research_question = context['research_question']
        new_theme_selected = request.params.get('theme', None)

        theme_options = []
        theme_list = get_action(u'theme_list')(context, {})
        for theme in theme_list.get(u'data', []):
            opt = {u'text': theme[u'title'], u'value': theme[u'id']}
            theme_options.append(opt)

        sub_theme_options = []

        if new_theme_selected:
            theme = new_theme_selected
        else:
            theme = research_question['theme']

        sub_theme_list = get_action(u'sub_theme_list')(context, {'theme': theme})

        for sub_theme in sub_theme_list.get(u'data', []):
            opt = {u'text': sub_theme[u'title'], u'value': sub_theme[u'id']}
            sub_theme_options.append(opt)

        if research_question:
            image = research_question.get('image_url', '')
            if not (image.startswith('http') or image.startswith('https')):
                research_question['image_url'] = image.split('/')[-1]

        if data:
            image = data.get('image_url', '')
            if not (image.startswith('http') or image.startswith('https')):
                data['image_url'] = image.split('/')[-1]

        form_vars = {
            u'id': research_question.get('id', ''),
            u'user': context.get('user'),
            u'data': data or research_question,
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
                    logic.tuplize_dict(logic.parse_params(request.form))))
        except dictization_functions.DataError:
            abort(400, _(u'Integrity Error'))

        print(data_dict)

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
                        upload = uploader.get_uploader('research_questions', image_url)
                        upload.update_data_dict(data_dict,
                                                'url',
                                                'upload',
                                                'False')
                        upload.upload()
                        data_dict['image_url'] = h.url_for_static('uploads/research_questions/%s' % upload.filename)
                    except ValidationError as e:
                        errors = e.error_dict
                        error_summary = e.error_summary
                        return self.get(data_dict, errors, error_summary)
        else:
            image_url = data_dict.get('image_url')
            if not image_url or image_url == 'placeholder-rq.png':
                data_dict['image_url'] = h.url_for_static('/base/images/placeholder-rq.png')
            elif not (image_url.startswith('http') or image_url.startswith('https')):
                data_dict['image_url'] = h.url_for_static('uploads/research_questions/%s' % image_url)

        try:
            research_question = get_action(
                u'research_question_update')(context, data_dict)
        except NotAuthorized:
            abort(403, _(u'Unauthorized to update this research question'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(name, data_dict, errors, error_summary)

        return h.redirect_to(u'research_question.read', name=research_question.get(u'name'))


research_question.add_url_rule(u'/', view_func=search, strict_slashes=False)
research_question.add_url_rule(
    u'/new', view_func=CreateView.as_view(str(u'new')))
research_question.add_url_rule(
    u'/edit/<name>', view_func=EditView.as_view(str(u'edit')))
research_question.add_url_rule(u'/<name>', view_func=read)
research_question.add_url_rule(
    u'/delete/<id>', view_func=delete, methods=(u'POST', ))
