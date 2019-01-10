from ckan.plugins import toolkit
from ckan import logic
from ckan import model

from ckanext.knowledgehub.model import SubThemes

from sqlalchemy import exc
from psycopg2 import errorcodes as pg_errorcodes


@toolkit.side_effect_free
def sub_theme_update(context, data_dict):
    try:
        logic.check_access('sub_theme_update', context, data_dict)
    except logic.NotAuthorized:
        raise logic.NotAuthorized(_(u'Need to be system administrator to administer'))

    id = logic.get_or_bust(data_dict, 'id')
    data_dict.pop('id')

    user = context.get('user')
    data_dict['modified_by'] = model.User.by_name(user.decode('utf8')).id

    try:
        filter = {'id': id}
        st = SubThemes.update(filter, data_dict)
    except exc.IntegrityError as e:
        if e.orig.pgcode == pg_errorcodes.UNIQUE_VIOLATION:
            raise logic.ValidationError({
                    'name': ['Already exists']
                })
        raise

    return SubThemes.get(**filter).first().as_dict()