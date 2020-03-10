import click

import ckan.plugins.toolkit as toolkit
from ckan.model import package_table, Session
from ckanext.knowledgehub.lib.quality import (
    Accuracy,
    Uniqueness,
    Validity,
    Timeliness,
    Consistency,
    Completeness,
    DataQualityMetrics
)
from logging import getLogger


log = getLogger(__name__)


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

        def _process_batch(packages):
            for pkg in packages:
                try:
                    metrics.calculate_metrics_for_dataset(pkg)
                except Exception as e:
                    log.error('Failed to calculate metrics for %s. Error: %s',
                              pkg, str(e))
                    log.exception(e)

        all_packages(_process_batch)

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


def all_packages(handler):
    offset = 0
    limit = 64
    while True:
        log.debug('Fetching dataset batch %d to %d', offset, offset+limit)
        query = Session.query(package_table.c.id)
        query = query.offset(offset).limit(limit)

        count = 0
        packages = []
        for result in query.all():
            packages.append(result[0])
            count += 1

        if not count:
            log.debug('No more packages to process.')
            break

        offset += limit

        try:
            log.debug('Processing %d packages in current batch.', count)
            handler(packages)
        except Exception as e:
            log.error('Failed to process package batch. Error: %s', str(e))
            log.exception(e)
