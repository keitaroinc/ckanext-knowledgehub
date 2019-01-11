import ckan.lib.dictization
import ckan.plugins.toolkit as toolkit
import ckan.lib.navl.dictization_functions as df
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.logic.schema import research_question_schema

import logging
import datetime


log = logging.getLogger(__name__)

_table_dictize = ckan.lib.dictization.table_dictize
_check_access = toolkit.check_access


def research_question_update(context, data_dict):
    """Update research question.

    :param content: The research question.
    :type content: string
    :param theme: Theme of the research question.
    :type value: string
    :param sub_theme: SubTheme of the research question.
    :type value: string
    :param state: State of the research question. Default is active.
    :type state: string
    """
    _check_access('research_question_update', context)

    data, errors = df.validate(data_dict, research_question_schema(), context)

    if errors:
        raise toolkit.ValidationError(errors)

    id = data.get('id')
    theme = data.get('theme')
    sub_theme = data.get('sub_theme')
    content = data.get('content')

    research_question = ResearchQuestion.get(id=id)
    research_question.theme = theme
    research_question.sub_theme = sub_theme
    research_question.content = content
    research_question.modified = datetime.datetime.now()
    research_question.save()

    return _table_dictize(research_question, context)
