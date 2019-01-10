from ckan.plugins import toolkit

not_empty = toolkit.get_validator('not_empty')

def research_question_schema():
    return {
        'content': [not_empty, unicode],
        'theme': [not_empty, unicode],
        'sub_theme': [not_empty, unicode]
    }
