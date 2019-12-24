import ckan.plugins.toolkit as toolkit


@toolkit.auth_allow_anonymous_access
def research_question_show(context, data_dict):
    return {'success': True}


@toolkit.auth_allow_anonymous_access
def research_question_list(context, data_dict):
    return {'success': True}


@toolkit.auth_allow_anonymous_access
def dashboard_list(context, data_dict):
    return {'success': True}


@toolkit.auth_allow_anonymous_access
def dashboard_show(context, data_dict):
    return {'success': True}


def intent_list(context, data_dict):
    # sysadmins only
    return {'success': False}
