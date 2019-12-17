import click
from logging import getLogger

logger = getLogger(__name__)


@click.group(u'intents')
def intents():
    pass

@index.command('update', short_help='Update the user intent entries from the latest queries.')
def update_intents():
    logger.info('Updating the latest user intents...')

@index.command('rebuild', short_help='Rebuild all user intents. Drops all then rebuilds all anew.')
def rebuild_intents():
    logger.info('Rebuilding all user intents...')