from ckan.plugins import toolkit
from ckan import logic
from ckan import model
from ckan import lib

from ckanext.knowledgehub.logic import schema as knowledgehub_schema
from ckanext.knowledgehub.model import SubThemes

from sqlalchemy import exc
from psycopg2 import errorcodes as pg_errorcodes


_df = lib.navl.dictization_functions


@toolkit.side_effect_free
def sub_theme_update(context, data_dict):
    ''' Updates an existing sub-theme

    :param name: name of the sub-theme
    :type name: string
    :param description: a description of the sub-theme (optional)
    :type description: string
    :param theme_id: the ID of the theme
    :type: string

    :returns: the updated sub-theme
    :rtype: dictionary
    '''

    try:
        logic.check_access('sub_theme_update', context, data_dict)
    except logic.NotAuthorized:
        raise logic.NotAuthorized(_(u'Need to be system administrator to administer'))

    id = logic.get_or_bust(data_dict, 'id')
    data_dict.pop('id')

    data, errors = _df.validate(data_dict, knowledgehub_schema.sub_theme_update(), context)
    if errors:
        raise logic.ValidationError(errors)

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

    return st.as_dict()