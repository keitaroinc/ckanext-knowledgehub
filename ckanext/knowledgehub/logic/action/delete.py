import logging

from ckan.model.meta import Session

import ckan.logic as logic
from ckan.plugins import toolkit
from ckan.common import _

from ckanext.knowledgehub.model import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.model import Dashboard


log = logging.getLogger(__name__)

check_access = toolkit.check_access
ValidationError = toolkit.ValidationError
NotAuthorized = toolkit.NotAuthorized
NotFound = logic.NotFound


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
