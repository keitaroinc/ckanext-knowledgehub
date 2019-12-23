import click
from logging import getLogger

from ckanext.knowledgehub.lib.ml.worker import Worker
from ckanext.knowledgehub.lib.intents import UserIntentsWorker, intents_extractor

logger = getLogger(__name__)


class UpdateIntentsWorker(Worker):

    def __init__(self,
                 worker_id,
                 heartbeat_interval=60000,
                 action='update'):
        super(UpdateIntentsWorker, self).__init__(worker_id, heartbeat_interval)
        self.intents_worker = UserIntentsWorker(intents_extractor)
        self.action = action

    def update_intents(self):
        self.intents_worker.update_latest()

    def rebuild(self):
        self.intents_worker.rebuild()

    def worker_run(self):
        if self.action == 'update':
            return self.update_intents()
        else:
            self.rebuild()


@click.group(u'intents')
def intents():
    pass

@intents.command('update', short_help='Update the user intent entries from the latest queries.')
def update_intents():
    logger.info('Updating the latest user intents...')
    worker = UpdateIntentsWorker('cli_intents_worker', action='update')
    worker.run()

@intents.command('rebuild', short_help='Rebuild all user intents. Drops all then rebuilds all anew.')
def rebuild_intents():
    logger.info('Rebuilding all user intents...')
    worker = UpdateIntentsWorker('cli_intents_worker', action='rebuild')
    worker.run()