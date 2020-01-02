'''Base classes and tools for workers related to ML and NLP processing.
'''


import time
from logging import getLogger
from threading import Thread, Event
from time import sleep
from ckan.lib.redis import connect_to_redis


class Worker(object):
    '''Base worker process.

    A worker performs a long-running operation, such as training of a ML model
    or predictions on large amount of data.

    Each worker can run as a separate process independently of of other
    workers. However, because the worker can be interrupted and/or fail
    unpredictably, when the worker resumes (starts up) it must know if the job
    has beed taken over by other worker. This base class implements a
    heart-beat based algorithm for synchronization between workers. The
    synchronization is based on the worker ID (usually the worker type) and a
    heartbeat interval.

    When the worker starts up, it also starts a heartbeat - it writes an entry
    to a shared storage and makes the entry to expire after a while (the heart
    beat interval). If the worker fails, the enry will be removed from the
    store automatically and other worker can resume the job.

    :param worker_id: ``str``, the ID of the worker.
    :param heartbeat_interval: ``int``, interval in milliseconds used to write
        the status in the store and also TTL of the entry.
    :param redis: ``redis``, redis connection. Optional. If not given, the
        CKAN default redis connection will be used.
    '''
    def __init__(self, worker_id, heartbeat_interval=60000, redis=None):
        self.worker_id = worker_id
        self.logger = getLogger('ckanext.Worker:' + worker_id)
        self._redis = redis or connect_to_redis()
        self.heartbeat_interval = heartbeat_interval
        self.running = False
        self._hb_thread = None
        self._hb_thread_stop = Event()

    def _hb_key(self):
        return 'ckan:worker:%s:heartbeat' % self.worker_id

    def run_heart_beat(self):
        '''Starts the heart-beat process.
        '''
        expire_in = int((self.heartbeat_interval/1000.0) + 1)
        wait_interval = self.heartbeat_interval/1000.0

        def _run_heart_beat():
            while self.running:
                self._redis.setex(self._hb_key(), 'RUNNING', expire_in)
                self.logger.debug('Heartbeat tick.')
                self._hb_thread_stop.wait(wait_interval)

        self._hb_thread = Thread(target=_run_heart_beat)
        self._hb_thread.start()
        self.logger.debug('Heartbeat started @' +
                          '%f' % wait_interval +
                          's and expires in ' +
                          str(expire_in) +
                          ' seconds.')

    def stop_heart_beat(self):
        '''Stops the heart-beat for this worker.

        This method blocks until the heart-beat thread has completed and the
        entry have been deleted from the shared store.
        '''
        self._hb_thread_stop.set()
        if self._hb_thread:
            self._hb_thread.join()
        self._redis.delete(self._hb_key())

    def other_worker_alive(self):
        '''Check if another worker have taken over the current job and if so,
        is it still alive.

        :returns: `True` if another worker have taken over the job, otherwise
            `False`.
        '''
        val = self._redis.get(self._hb_key())
        return val is not None

    def _wait_to_run(self):
        wait_time = self.heartbeat_interval + 1000
        start = time.time() * 1000
        self.logger.debug('Checking if another instance of ' +
                          'this worker is running...')
        while True:
            curr = time.time() * 1000
            if not self.other_worker_alive():
                self.logger.debug('It does not. This worker can run now.')
                return True
            if curr - start >= wait_time:
                break
            sleep(0.5)
        self.logger.info('It seems that another instance ' +
                         'of this worker is already running.')
        return False

    def run(self, once=True):
        '''Runs the worker.

        First, a check is being performed for the current job.

        If this worker can take and execute the job, first the hearbeat is
        started, then the job is executed.

        If this is a one-time job, then right after the job is completed,
        Worker stop is issued.
        If it is a long-runnign repeatable job, then the method just exits
        without calling `stop` on itself.

        :param once: ``bool``, `True` if this is a one-time job and the worker
            needs to stop right after it completes the job. This is the default
            setting for the worker.
        '''
        self.logger.info('Starting.')
        if not self._wait_to_run():
            self.stop()
            return
        self.running = True
        self.run_heart_beat()
        try:
            self.logger.info('Running worker task...')
            self.worker_run()
            self.logger.info('Worker task completed.')
        except Exception as e:
            self.logger.error('Task run failed with error. ' +
                              'Shutting down. Error:' + str(e))
            self.logger.exception(e)
            self.stop()
            return

        if once:
            self.logger.debug('One time task only. Stopping immediately...')
            self.stop()

    def stop(self):
        '''Stops this worker.

        The heartbeat is stopped and the state is set to not running
        (`running=False`).
        '''
        self.logger.debug('Stopping worker...')
        self.running = False
        self.stop_heart_beat()
        self.logger.info('Worker stopped.')

    def worker_run(self):
        '''Called to execute the actual job.

        This method is called when all of the criteria are satisfied to run the
        actual job that the worker should perform.

        It is intended to be implemented in an actial implementation of the
        worker.
        '''
        pass


class ModelTrainWorker(Worker):
    '''Specialization of the Worker for training of ML models.
    '''
    def __init__(self, worker_id, hb_time=60000, redis=None):
        super(ModelTrainWorker, self).__init__(worker_id, hb_time, redis)
        self._wait = Event()
        self._scheduled = None

    def worker_run(self):
        self._wait.wait()
        if self._scheduled:
            self._scheduled()

    def train_model(self, model_name, train_data, model_version=None):
        self._scheduled = lambda: self.do_train_model(model_name,
                                                      train_data,
                                                      model_version)
        self._wait.set()

    def do_train_model(self, model_name, train_data, model_version=None):
        pass
