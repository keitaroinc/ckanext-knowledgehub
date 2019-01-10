import ckan.plugins.toolkit as toolkit


@toolkit.auth_disallow_anonymous_access
def research_question_create(context, data_dict):
    return {'success': True}
