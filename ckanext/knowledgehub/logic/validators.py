import re
from six import string_types

import ckan.plugins as p
import ckan.lib.navl.dictization_functions as df
import ckan.lib.dictization
from ckanext.knowledgehub.model.theme import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.model import Dashboard
from ckanext.knowledgehub.model import UserIntents
from ckanext.knowledgehub.model import UserQueryResult

_table_dictize = ckan.lib.dictization.table_dictize


def theme_name_validator(key, data, errors, context):
    session = context['session']
    theme_name = context.get('theme')

    if theme_name and theme_name == data[key]:
        return

    query = session.query(Theme.name).filter_by(name=data[key])

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This theme name already exists. '
                        'Choose another one.'))


def sub_theme_name_validator(key, data, errors, context):
    session = context['session']
    sub_theme_name = context.get('sub_theme')

    if sub_theme_name and sub_theme_name == data[key]:
        return

    query = session.query(SubThemes.name).filter_by(name=data[key])

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This sub-theme name already exists. '
                        'Choose another one.'))


def research_question_name_validator(key, data, errors, context):
    session = context['session']
    research_question_name = context.get('research_question_name')

    if research_question_name and research_question_name == data[key]:
        return

    query = session.query(ResearchQuestion.name).filter_by(name=data[key])

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This research question name already exists. '
                        'Choose another one.'))


def research_question_title_validator(key, data, errors, context):
    session = context['session']

    research_question_title = context.get('research_question_title')

    if research_question_title and research_question_title == data[key]:
        return

    query = session.query(ResearchQuestion.name).filter_by(title=data[key])

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This research question already exists. '
                        'Choose another one.'))


def research_question_title_characters_validator(key, data, errors, context):
    '''Return the given value if it's a valid research question,
     otherwise return appropriate error.
    '''
    title_match = re.compile("[a-zA-Z0-9_\-. ?]*$")
    if not isinstance(data[key], string_types):
        errors[key].append(
            p.toolkit._('Research question must be strings'))

    # check basic textual rules
    if data[key] in ['new', 'edit', 'search']:
        errors[key].append(
            p.toolkit._('That research question '
                        'cannot be used'))

    if len(data[key]) < 2:
        errors[key].append(
            p.toolkit._('Must be at least %s '
                        'characters long') % 2)

    # Title should not be limited to max size and may contain other characters


def check_sub_theme_parent(key, data, errors, context):
    session = context['session']
    clean_data = df.unflatten(data)

    theme = clean_data.get('theme')
    sub_theme = clean_data.get('sub_theme')

    if sub_theme:
        children_list = []
        db_list = session.query(SubThemes.id).filter_by(theme=theme).all()

        children_list = [e[0] for e in db_list]

        if sub_theme not in children_list:
            errors[key].append(p.toolkit._('Sub-theme must belong to theme.'))


def dashboard_name_validator(key, data, errors, context):
    session = context['session']
    dashboard_name = context.get('dashboard')

    if dashboard_name and dashboard_name == data[key]:
        return

    query = session.query(Dashboard.name).filter_by(name=data[key])

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This dashboard name already exists. '
                        'Choose another one.'))


def dashboard_type_validator(key, data, errors, context):
    clean_data = df.unflatten(data)
    dashboard_type = clean_data.get('type')

    if dashboard_type != 'internal' and dashboard_type != 'external':
        errors[key].append(
            p.toolkit._(
                'The dashboard type can be either `internal` or `external`'))


def dashboard_source_validator(key, data, errors, context):
    clean_data = df.unflatten(data)
    dashboard_type = clean_data.get('type')
    dashboard_source = clean_data.get('source')

    if dashboard_type == 'external' and\
            (dashboard_source is None or dashboard_source == ''):
        errors[key].append(
            p.toolkit._('Missing value'))


def resource_feedbacks_type_validator(key, data, errors, context):
    clean_data = df.unflatten(data)
    rf_type = clean_data.get('type')

    rf_types = ['useful', 'unuseful', 'trusted', 'untrusted']

    if rf_type not in rf_types:
        errors[key].append(
            p.toolkit._(
                'Allowed resource feedback types are: %s' % ', '.join(rf_types)
            )
        )


def kwh_data_type_validator(key, data, errors, context):
    clean_data = df.unflatten(data)
    rf_type = clean_data.get('type')

    rf_types = ['theme', 'sub-theme', 'rq', 'search']

    if rf_type not in rf_types:
        errors[key].append(
            p.toolkit._(
                'Allowed KWH data types are: %s' % ', '.join(rf_types)
            )
        )


def user_intent_query_id_validator(key, data, errors, context):
    session = context['session']

    query = session.query(UserIntents.user_query_id).filter_by(
        user_query_id=data.get(key))

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This user_query_id already exists. '
                        'Choose another one.'))


def user_query_result_query_id(key, data, errors, context):
    session = context['session']

    query = session.query(UserQueryResult.query_id).filter_by(
        query_id=data.get(key))

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This query_id already exists. '
                        'Choose another one.'))


def long_name_validator(max_length=500):
    '''Returns a validator function for validating names with given max size.
    '''

    def _long_name_validator(value, context):
        '''Return the given value if it's a valid name, otherwise raise Invalid.

        If it's a valid name, the given value will be returned unmodified.

        This function applies general validation rules for names of packages,
        groups, users, etc.

        This validator is different from CKAN's own name_validator in that this
        validator allows for custom max length of the name.

        :raises ckan.lib.navl.dictization_functions.Invalid: if ``value`` is not
            a valid name

        '''
        name_match = re.compile('[a-z0-9_\-]*$')
        if not isinstance(value, string_types):
            raise Invalid(_('Names must be strings'))

        # check basic textual rules
        if value in ['new', 'edit', 'search']:
            raise Invalid(_('That name cannot be used'))

        if len(value) < 2:
            raise Invalid(_('Must be at least %s characters long') % 2)
        if max_length is not None:
            if len(value) > max_length:
                raise Invalid(_('Name must be a maximum of '
                                '%i characters long') % \
                            max_length)
        if not name_match.match(value):
            raise Invalid(_('Must be purely lowercase alphanumeric '
                            '(ascii) characters and these symbols: -_'))
        return value

    return _long_name_validator
