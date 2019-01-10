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


@toolkit.side_effect_free
def research_question_list(context, data_dict):
    rq_list = []

    rq_db_list = ResearchQuestion.all()

    for e in rq_db_list:
        rq_list.append(_table_dictize(e, context))

    return rq_list
