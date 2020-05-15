import logging
from datetime import datetime

from ckan.model.meta import Session

import ckan.logic as logic
from ckan.logic.action.delete import (
    resource_view_delete as _resource_view_delete
)
from ckan.plugins import toolkit
from ckan.common import _
from ckan import model
from ckan.model import Session
from ckan.logic.action.delete import package_delete as ckan_package_delete

from hdx.data.dataset import Dataset

from ckanext.knowledgehub import helpers as plugin_helpers
from ckanext.knowledgehub.model import (
    Dashboard,
    Theme,
    SubThemes,
    ResearchQuestion,
    Visualization,
    UserIntents,
    ResourceValidate,
    Keyword,
    KWHData,
    Posts,
    Comment,
)
from ckanext.knowledgehub.logic.jobs import schedule_update_index


log = logging.getLogger(__name__)

check_access = toolkit.check_access
ValidationError = toolkit.ValidationError
NotAuthorized = toolkit.NotAuthorized
NotFound = logic.NotFound
_get_or_bust = logic.get_or_bust


def theme_delete(context, data_dict):
    '''
    Deletes existing analytical
    framework Theme by id
    :param id
    '''
    check_access('theme_delete', context)

    if 'id' not in data_dict:
        raise ValidationError({"id": _('Missing value')})

    sub_themes = Session.query(SubThemes) \
        .filter_by(theme=data_dict['id']) \
        .count()
    if sub_themes:
        raise ValidationError(_('Theme cannot be deleted while it '
                                'still has sub-themes'))
    # TODO we might need to change the
    #  status of the theme and child elements
    #  when deleting theme
    Theme.delete({'id': data_dict['id']})

    return {"message": _('Theme deleted.')}


@toolkit.side_effect_free
def sub_theme_delete(context, data_dict):
    ''' Deletes a sub-theme

    :param id: the sub-theme's ID
    :type id: string

    :returns: OK
    :rtype: string
    '''

    try:
        check_access('sub_theme_delete', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system '
                              u'administrator to administer'))

    id = logic.get_or_bust(data_dict, 'id')

    questions = Session.query(ResearchQuestion) \
        .filter_by(sub_theme=id) \
        .count()
    if questions:
        raise logic.ValidationError(_('Sub-Theme cannot be deleted while it '
                                      'still has research questions'))

    try:
        filter = {'id': id}
        SubThemes.delete(filter)
    except NotFound:
        raise NotFound(_(u'Sub-theme'))

    return 'OK'


def research_question_delete(context, data_dict):
    '''Delete research question.

    :param id: Research question database id.
    :type id: string
    '''
    check_access('research_question_delete', context)

    id = data_dict.get('id')
    if not id:
        raise ValidationError({'id': 'Missing parameter'})

    ResearchQuestion.delete(id=id)

    # Delete from index
    ResearchQuestion.delete_from_index({'id': id})
    log.info("Research question id \'{}\' deleted successfully".format(id))


def dashboard_delete(context, data_dict):
    '''
    Deletes existing dashboard by id
    :param id
    '''
    check_access('dashboard_delete', context)

    if 'id' not in data_dict:
        raise ValidationError({"id": _('Missing value')})

    Dashboard.delete({'id': data_dict['id']})

    # Delete from index
    Dashboard.delete_from_index({'id': data_dict['id']})

    return {"message": _('Dashboard deleted.')}


def resource_view_delete(context, data_dict):
    resource_view = logic.get_action('resource_view_show')(context, data_dict)
    plugin_helpers.remove_rqs_from_dataset(resource_view)
    _resource_view_delete(context, data_dict)
    Visualization.delete_from_index({'id': resource_view['id']})


@toolkit.side_effect_free
def user_intent_delete(context, data_dict):
    ''' Deletes a intent

    :param id: the intent ID
    :type id: string

    :returns: OK
    :rtype: string
    '''

    try:
        check_access('user_intent_delete', context, data_dict)
    except NotAuthorized:
        raise NotAuthorized(_(u'Need to be system '
                              u'administrator to administer'))

    id = logic.get_or_bust(data_dict, 'id')
    UserIntents.delete({'id': id})

    return 'OK'


def resource_validate_delete(context, data_dict):
    '''
    Deletes existing validation report of resource by id
    :param id
    '''

    check_access('resource_validate_delete', context)
    if 'id' not in data_dict:
        raise ValidationError({"resource": _('Missing value')})

    ResourceValidate.delete({'resource': data_dict['id']})

    return {"message": _('Validation report of the resource is deleted.')}


def member_delete(context, data_dict=None):
    '''Remove an object (e.g. a user, dataset or group) from a group.

    You must be authorized to edit a group to remove objects from it.

    :param id: the id of the group
    :type id: string
    :param object: the id or name of the object to be removed
    :type object: string
    :param object_type: the type of the object to be removed, e.g. ``package``
        or ``user``
    :type object_type: string

    '''
    model = context['model']

    group_id, obj_id, obj_type = _get_or_bust(
        data_dict, ['id', 'object', 'object_type'])

    group = model.Group.get(group_id)
    if not group:
        raise NotFound('Group was not found.')

    obj_class = logic.model_name_to_class(model, obj_type)
    obj = obj_class.get(obj_id)
    if not obj:
        raise NotFound('%s was not found.' % obj_type.title())

    check_access('member_delete', context, data_dict)

    member = model.Session.query(model.Member).\
        filter(model.Member.table_name == obj_type).\
        filter(model.Member.table_id == obj.id).\
        filter(model.Member.group_id == group.id).\
        filter(model.Member.state == 'active').first()
    if member:
        rev = model.repo.new_revision()
        rev.author = context.get('user')
        rev.message = _(u'REST API: Delete Member: %s') % obj_id
        member.delete()
        model.repo.commit()

    if obj_type == 'package':
        plugin_helpers.views_dashboards_groups_update(data_dict.get('object'))


def keyword_delete(context, data_dict):
    '''Remove a keyword by its id or name.

    If the keyword contains tags, those will be set as free tags and will not
    be removed from the system.

    :param id: `str`, the id or the name of the keyword to remove.
    '''
    check_access('keyword_delete', context)
    if 'id' not in data_dict:
        raise ValidationError({'id': _('Missing Value')})

    keyword = toolkit.get_action('keyword_show')(context, data_dict)

    for tag in Keyword.get_tags(keyword['id']):
        tag.keyword_id = None
        tag.save()

    Session.delete(Keyword.get(keyword['id']))
    Session.commit()

    schedule_update_index(keyword['name'])


def tag_delete_by_name(context, data_dict):
    '''
    Remove a tag by its name
    :param name: `str`, the name of the tag to remove.
    '''
    model = context['model']

    if not data_dict['name']:
        raise ValidationError({'name': _('name not in data')})
    tag_name = _get_or_bust(data_dict, 'name')

    vocab_id_or_name = data_dict.get('vocabulary_id')

    tag_obj = model.tag.Tag.get(tag_name, vocab_id_or_name)

    if tag_obj is None:
        raise NotFound(_('Could not find tag "%s"') % tag_name)

    check_access('tag_delete_by_name', context, data_dict)

    tag_obj.delete()
    model.repo.commit()


def delete_tag_in_rq(context, data_dict):
    '''
    Remove tag in research question
    :param id: `str`, id of the research question.
    :param tag: `str`, the name of the tag to be removed.
    '''
    id = data_dict.get("id")
    if not id:
        raise ValidationError({'id': _('Missing value')})
    id_or_name = data_dict.get('id') or data_dict.get('name')
    tag_to_delete = data_dict.get('tag')

    research_question = ResearchQuestion.get(id_or_name=id_or_name).first()
    if not research_question:
        log.debug('Could not find research question %s', id)

    rq_dict = research_question.as_dict()

    tag_list = rq_dict.get('tags').split(',')
    if len(tag_list) == 1:
        result = toolkit.get_action('research_question_update')(context, {
                'id': rq_dict.get('id'),
                'name': rq_dict.get('name'),
                'title': rq_dict.get('title'),
                'tags': None
                })
    else:
        for tag in tag_list:
            if tag == tag_to_delete:
                tag_list.remove(tag_to_delete)
        str1 = ","
        tags = str1.join(tag_list)

        result = toolkit.get_action('research_question_update')(context, {
                    'id': rq_dict.get('id'),
                    'name': rq_dict.get('name'),
                    'title': rq_dict.get('title'),
                    'tags': tags
                    })

    return result


def delete_tag_in_dash(context, data_dict):
    '''
    Remove tag in dashboard
    :param id: `str`, id of the dashboard.
    :param tag: `str`, the name of the tag to be removed.
    '''
    id = data_dict.get("id")
    tag_name = data_dict.get('tag')
    if not id:
        raise ValidationError({'id': _('Missing value')})

    dash = Dashboard.get(id)

    if not dash:
        log.debug('Could not find dashboard %s', id)
    dash_dict = dash.as_dict()
    tag_list = dash_dict.get('tags').split(',')
    if len(tag_list) == 1:
        result = toolkit.get_action('dashboard_update')(context, {
                'id': dash_dict.get('id'),
                'name': dash_dict.get('name'),
                'title': dash_dict.get('title'),
                'description': dash_dict.get('description'),
                'type': dash_dict.get('type'),
                'source': dash_dict.get('source'),
                'indicators': dash_dict.get('indicators'),
                'created_by': dash_dict.get('created_by'),
                'tags': None
                })
    else:
        for tag in tag_list:
            if tag == tag_name:
                tag_list.remove(tag)
        str1 = ","
        tags = str1.join(tag_list)

        result = toolkit.get_action('dashboard_update')(context, {
                    'id': dash_dict.get('id'),
                    'name': dash_dict.get('name'),
                    'title': dash_dict.get('title'),
                    'description': dash_dict.get('description'),
                    'type': dash_dict.get('type'),
                    'source': dash_dict.get('source'),
                    'indicators': dash_dict.get('indicators'),
                    'created_by': dash_dict.get('created_by'),
                    'tags': tags
                    })

    return result


def delete_tag_in_rv(context, data_dict):
    '''
    Remove tag in resource view
    :param id: `str`, id of the resource view.
    :param tag: `str`, the name of the tag to be removed.
    '''
    tag_name = data_dict.get('tag')
    id = data_dict.get("id")
    if not id:
        raise ValidationError({'id': _('Missing value')})

    visual = model.Session.query(model.ResourceView).filter_by(id=id)
    if not visual:
        log.debug('Could not find visualization %s', id)
    visual_element = visual.order_by(model.ResourceView.order).all()[0]

    visual_dict = {
        'id': visual_element.id,
        'resource_id': visual_element.resource_id,
        'title': visual_element.title,
        'description': visual_element.description,
        'view_type': visual_element.view_type,
        'order': visual_element.order,
        'config': visual_element.config,
        'tags': visual_element.tags
    }

    if visual_dict.get('tags'):
        tag_list = visual_dict.get('tags').split(',')
        if len(tag_list) == 1:
            visual_element.tags = None
            visual_element.save()
            visual_element.commit()
            return visual_element
        else:
            for tag in tag_list:
                if tag == tag_name:
                    tag_list.remove(tag)
                    str1 = ","
                    tags = str1.join(tag_list)
                    visual_element.tags = tags
                    visual_element.save()
                    visual_element.commit()

                    return visual_element


# Overwrite of the original 'tag_delete'
def tag_delete(context, data_dict):
    '''Delete a tag.

    You must be a sysadmin to delete tags.

    :param id: the id or name of the tag
    :type id: string
    :param vocabulary_id: the id or name of the vocabulary that the tag belongs
        to (optional, default: None)
    :type vocabulary_id: string

    '''

    model = context['model']

    if 'id' not in data_dict or not data_dict['id']:
        raise ValidationError({'id': _('id not in data')})
    tag_id_or_name = _get_or_bust(data_dict, 'id')

    vocab_id_or_name = data_dict.get('vocabulary_id')

    tag_obj = model.tag.Tag.get(tag_id_or_name, vocab_id_or_name)
    tag_name = tag_obj.name

    if tag_obj is None:
        raise NotFound(_('Could not find tag "%s"') % tag_id_or_name)

    check_access('tag_delete', context, data_dict)

    rq_list = toolkit.get_action('rqs_search_tag')(context, {
        'tags': tag_name
    })
    list_dashboard = toolkit.get_action('dash_search_tag')(context, {
        'tags': tag_name
    })
    list_visuals = toolkit.get_action('visual_search_tag')(context, {
        'tags': tag_name
    })

    if len(rq_list):
        for rq in rq_list:
            toolkit.get_action('delete_tag_in_rq')(context, {
                'id': rq,
                'tag': tag_name
            })
    if len(list_dashboard):
        for dash in list_dashboard:
            toolkit.get_action('delete_tag_in_dash')(context, {
                'id': dash,
                'tag': tag_name
            })
    if len(list_visuals):
        for visual in list_visuals:
            toolkit.get_action('delete_tag_in_rv')(context, {
                'id': visual,
                'tag': tag_name
            })

    tag_obj.delete()
    model.repo.commit()

    return {"message": _('The tag is deleted.')}


def package_delete(context, data_dict):
    '''Delete a dataset (package).

    This makes the dataset disappear from all web & API views, apart from the
    trash.

    You must be authorized to delete the dataset.

    :param id: the id or name of the dataset to delete
    :type id: string

    '''

    ckan_package_delete(context, data_dict)
    try:
        KWHData.delete({'dataset': data_dict['id']})
    except Exception as e:
        log.debug('Cannot remove dataset from kwh data %s' % str(e))


def delete_resource_from_hdx(context, data_dict):

    check_access('package_update', context)
    id = data_dict.get('id')
    if not id:
        raise ValidationError('Dataset id is missing!')
    res_id = data_dict.get('resource_id')
    resource = toolkit.get_action('resource_show')(context,
                                                   {'id': res_id})

    try:

        data = logic.get_action('package_show')(
            {'ignore_auth': True},
            {'id': id})

        hdx_dataset = Dataset.read_from_hdx(data['name'])

        for hdx_resource in hdx_dataset.get_resources():
            if hdx_resource['name'] == data_dict['resource_name']:
                hdx_resource.delete_from_hdx()
                resource['hdx_name_resource'] = ""
                try:
                    resource = toolkit.get_action('resource_update')(context,
                                                                     resource)
                except ValidationError as e:
                    try:
                        raise ValidationError(e.error_dict)
                    except (KeyError, IndexError):
                        raise ValidationError(e.error_dict)
                return
        return "Dataset not found!"
    except Exception as e:
        log.debug(e)
        return e


def delete_package_from_hdx(context, data_dict):

    check_access('package_update', context)

    id = data_dict.get('id')
    if not id:
        raise ValidationError('Dataset id is missing!')

    try:
        data = logic.get_action('package_show')(
            {'ignore_auth': True},
            {'id': id})

        hdx_dataset = Dataset.read_from_hdx(data['name'])
        if hdx_dataset:
            hdx_dataset.delete_from_hdx()
            data['hdx_name'] = ""
            try:
                toolkit.get_action('package_update')(context, data)
            except ValidationError as e:
                try:
                    raise ValidationError(e.error_dict)
                except (KeyError, IndexError):
                    raise ValidationError(e.error_dict)

            return
        return "Dataset not found!"
    except Exception as e:
        log.debug(e)
        return "Please try again!"


def post_delete(context, data_dict):
    '''Deletes a newsfeed post.

    Only sysadmins and the post author can delete the post.

    :param id: `str`, the post ID. Required.
    '''
    if 'id' not in data_dict:
        raise logic.ValidationError({
            'id': _('Missing Value'),
        })

    user = context.get('auth_user_obj')
    if not user:
        raise logic.NotAuthorized(_('You are not authorized to '
                                    'delete this post'))

    post = Posts.get(data_dict['id'])
    if not post:
        raise logic.NotFound(_('Post not found'))

    is_sysadmin = hasattr(user, 'sysadmin') and user.sysadmin
    skip_auth = context.get('ignore_authentication')

    if not (is_sysadmin or skip_auth):
        if post.created_by != user.id:
            raise logic.NotAuthorized(_('You are not authorized to '
                                        'delete this post'))
    try:
        toolkit.get_action('delete_comments')(context, {
            'ref': post.id,
        })
        model.Session.delete(post)
        model.Session.commit()
        Posts.delete_from_index(data_dict)
    except Exception as e:
        log.error('Failed to delete comments. Error: %s', str(e))
        log.exception(e)
        model.Session.rollback()


def delete_comments(context, data_dict):
    pass


def comment_delete(context, data_dict):
    check_access('comment_delete', context, data_dict)

    user = context.get('auth_user_obj')
    is_sysadmin = hasattr(user, 'sysadmin') and user.sysadmin

    comment_id = data_dict.get('id', '').strip()
    if not comment_id:
        raise ValidationError({'id': [_('Missing value')]})

    comment = Comment.get(comment_id)
    if not comment:
        raise NotFound(_('Comment not found'))

    if comment.created_by != user.id:
        if not is_sysadmin:
            raise NotAuthorized(_('You cannot delete this comment.'))

    if not comment.replies_count:
        # we can delete this comment completely
        Session.delete(comment)

        if comment.reply_to:
            Comment.decrement_reply_count(comment.ref, comment.reply_to)

        Session.flush()
        return

    # Comment has replies, so we just mark as deleted
    comment.delete = True
    comment.modified_at = datetime.now()
    comment.save()

    Session.flush()
