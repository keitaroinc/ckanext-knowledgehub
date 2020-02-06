import logging

from ckan.model.meta import Session

import ckan.logic as logic
from ckan.logic.action.delete import (
    resource_view_delete as _resource_view_delete
)
from ckan.plugins import toolkit
from ckan.common import _
from ckanext.knowledgehub import helpers as plugin_helpers


from ckanext.knowledgehub.model import Dashboard
from ckanext.knowledgehub.model import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.model import Visualization
from ckanext.knowledgehub.model import UserIntents
from ckanext.knowledgehub.model import ResourceValidate
from ckanext.knowledgehub import helpers as kwh_helpers


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
    plugin_helpers.remove_rqs_from_dataset(context, resource_view)
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
        kwh_helpers.views_dashboards_groups_update(data_dict.get('object'))
