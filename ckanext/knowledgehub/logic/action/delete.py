import ckan.plugins.toolkit as toolkit
import ckan.lib.navl.dictization_functions as df
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.logic.schema import research_question_delete_schema

import logging

log = logging.getLogger(__name__)

_check_access = toolkit.check_access


def research_question_delete(context, data_dict):
    """Delete research question.

    :param id: Research question database id.
    :type id: string
    """
    _check_access('research_question_delete', context, data_dict)

    data, errors = df.validate(data_dict, research_question_delete_schema(), context)

    if errors:
        raise toolkit.ValidationError(errors)

    id = data.get('id')
    ResearchQuestion.delete(id=id)
    log.info("Research question id \'{}\' deleted successfully".format(id))
