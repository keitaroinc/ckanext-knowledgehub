import ckan.plugins as p

from ckanext.knowledgehub.model.theme import Theme


def theme_name_validator(key, data, errors, context):
    session = context['session']
    theme_name = context.get('name')

    if theme_name and theme_name == data[key]:
        return

    query = session.query(Theme.name).filter_by(name=data[key])

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This theme name already exists. '
                        'Choose another one.'))
