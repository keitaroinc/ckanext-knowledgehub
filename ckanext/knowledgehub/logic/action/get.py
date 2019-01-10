from ckan.plugins import toolkit
from ckan import lib
from ckanext.knowledgehub.model import ResearchQuestion

_table_dictize = lib.dictization.table_dictize


@toolkit.side_effect_free
def research_question_show(context, data_dict):
    id = data_dict.get('id')
    rq = ResearchQuestion.get(id=id)

    if not rq:
        raise toolkit.NotFound

    return _table_dictize(rq, context)
