import click

import ckan.plugins.toolkit as toolkit
from ckanext.knowledgehub.lib.quality import (
    Accuracy,
    Uniqueness,
    Validity,
    Timeliness,
    Consistency,
    Completeness,
    DataQualityMetrics
)


@click.group('quality')
def quality():
    pass


@quality.command(u'calculate', help='Calculate data quality metrics')
@click.option('--dataset',
              default='all',
              help='Calculate quality metrics for dataset.')
@click.option('--dimension',
              default='all',
              help='Which metric to calculate.')
def calculate(dataset, dimension):
    _register_mock_translator()
    dimensions = ['completeness',
                  'uniqueness',
                  'timeliness',
                  'validity',
                  'accuracy',
                  'consistency']
    dimension_calculators = {
        'completeness': Completeness(),
        'uniqueness': Uniqueness(),
        'timeliness': Timeliness(),
        'validity': Validity(),
        'accuracy': Accuracy(),
        'consistency': Consistency(),
    }

    if dimension == 'all':
        calculators = [dimension_calculators[dim] for dim in dimensions]
    elif dimension not in dimensions:
        raise Exception('Invalid dimension specified. Valid dimensions are: ' +
                        ', '.join(dimensions))
    else:
        calculators = [dimension_calculators[dimension]]

    metrics = DataQualityMetrics(metrics=calculators)

    if dataset == 'all':
        # FIXME: Does not return private packages, but we need all active ones.
        for pkg in toolkit.get_action('package_list')({'ignore_auth': True},
                                                      {}):
            metrics.calculate_metrics_for_dataset(pkg['id'])
    else:
        metrics.calculate_metrics_for_dataset(dataset)


def _register_mock_translator():
    # Workaround until the core translation function defaults to the Flask one
    from paste.registry import Registry
    from ckan.lib.cli import MockTranslator
    registry = Registry()
    registry.prepare()
    from pylons import translator
    registry.register(translator, MockTranslator())