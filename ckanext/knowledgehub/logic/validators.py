import re
from six import string_types

import ckan.plugins as p
import ckan.lib.navl.dictization_functions as df
import ckan.lib.dictization
from ckanext.knowledgehub.model.theme import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.model import Dashboard

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
    title_match = re.compile("[a-zA-Z0-9_\-. ]*$")
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

    if len(data[key]) > 160:
        errors[key].append(
            p.toolkit._('Research question must be a '
                        'maximum of %i characters long') % 160)

    if not title_match.match(data[key]):
        errors[key].append(
            p.toolkit._('Must be purely lowercase alphanumeric '
                        '(ascii) characters and these symbols: -_.'))


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
