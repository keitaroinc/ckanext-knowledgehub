import ckan.plugins.toolkit as toolkit


@toolkit.auth_allow_anonymous_access
def research_question_show(context, data_dict):
    return {'success': True}
