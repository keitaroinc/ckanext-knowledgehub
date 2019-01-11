import ckan.authz as authz


def research_question_delete(context, data_dict):
    user = context.get('user')
    author = data_dict.get('author')
    if user == author or authz.is_sysadmin(user):
        return {'success': True}
    else:
        return {'success': False}
