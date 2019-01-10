import ckan.lib.dictization
import ckan.plugins.toolkit as toolkit
import ckan.lib.navl.dictization_functions as df
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.logic.schema import research_question_schema

import logging

log = logging.getLogger(__name__)

_table_dictize = ckan.lib.dictization.table_dictize
_check_access = toolkit.check_access


def research_question_create(context, data_dict):
    """Create new research question.

    :param content: The research question.
    :type content: string
    :param theme: Theme of the research question.
    :type value: string
    :param sub_theme: SubTheme of the research question.
    :type value: string
    :param state: State of the research question. Default is active.
    :type state: string
    """
    _check_access('research_question_create', context, data_dict)

    data, errors = df.validate(data_dict, research_question_schema(), context)

    if errors:
        raise toolkit.ValidationError(errors)

    user_obj = context.get('user_obj')
    user_id = user_obj.id

    theme = data.get('theme')
    sub_theme = data.get('sub_theme')
    content = data.get('content')
    state = data.get('state', 'active')

    research_question = ResearchQuestion(
        theme=theme,
        sub_theme=sub_theme,
        content=content,
        author=user_id,
        state=state
    )
    research_question.save()

    return _table_dictize(research_question, context)
