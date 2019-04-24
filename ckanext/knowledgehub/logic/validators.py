import ckan.plugins as p
from ckan import logic as logic
import ckan.lib.navl.dictization_functions as df
import ckan.lib.dictization
from ckanext.knowledgehub.model.theme import Theme
from ckanext.knowledgehub.model import SubThemes
from ckanext.knowledgehub.model import ResearchQuestion
from ckanext.knowledgehub.model import Dashboard
import ckanext.knowledgehub.helpers as extension_helpers

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
    research_question_name = context.get('research_question')

    if research_question_name and research_question_name == data[key]:
        return

    query = session.query(ResearchQuestion.name).filter_by(name=data[key])

    result = query.first()

    if result:
        errors[key].append(
            p.toolkit._('This research question name already exists. '
                        'Choose another one.'))


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
