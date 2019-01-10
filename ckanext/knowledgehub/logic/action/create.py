from ckan.common import _
from ckan.plugins import toolkit
from ckan import logic
from ckan import lib
from ckan import model

from ckanext.knowledgehub.logic import schema as knowledgehub_schema
from ckanext.knowledgehub.model import SubThemes

from sqlalchemy import exc
from psycopg2 import errorcodes as pg_errorcodes


df = lib.navl.dictization_functions


@toolkit.side_effect_free
def sub_theme_create(context, data_dict):
    try:
        logic.check_access('sub_theme_create', context, data_dict)
    except logic.NotAuthorized:
        raise logic.NotAuthorized(_(u'Need to be system administrator to administer'))

    data, errors = df.validate(data_dict, knowledgehub_schema.sub_theme_create(), context)
    if errors:
        raise logic.ValidationError(errors)

    user = context.get('user')
    data['created_by'] = model.User.by_name(user.decode('utf8')).id

    try:
        st = SubThemes(**data)
        st.save()
    except exc.IntegrityError as e:
        if e.orig.pgcode == pg_errorcodes.UNIQUE_VIOLATION:
            raise logic.ValidationError({
                    'name': ['Already exists']
                })
        raise

    return st.as_dict()