from datetime import datetime
from logging import getLogger
from threading import Thread, Event
from time import sleep
from ckan.lib.redis import connect_to_redis

class Worker:

    def __init__(self, worker_id, heartbeat_interval=60000):
        self.worker_id = worker_id
        self.logger = getLogger('Worker:' + worker_id)
        self._redis = connect_to_redis()
        self.heartbeat_interval = heartbeat_interval
        self.running = False
        self._hb_thread = None
        self._hb_thread_stop = Event()

    def _hb_key(self):
        return 'ckan:worker:%s:heartbeat' % self.worker_id

    def run_heart_beat(self):
        def _run_heart_beat():
            while self.running:
                self._redis.set(self._hb_key(), 'RUNNING')
                self._redis.expire(self._hb_key(), self.heartbeat_interval + 1000)
                self._hb_thread_stop.wait(self.heartbeat_interval/1000)
        
        self._hb_thread = Thread(target=_run_heart_beat)
        self._hb_thread.start()
    
    def stop_heart_beat(self):
        self._hb_thread_stop.set()
        if self._hb_thread:
            self._hb_thread.join()

    def other_worker_alive(self):
        val = self._redis.get(self._hb_key())
        return val is not None

    def _wait_to_run(self):
        wait_time = self.heartbeat_interval + 1000
        start = datetime.now().time() * 1000
        while True:
            sleep(0.5)
            curr = datetime.now().time() * 1000
            if not self.other_worker_alive():
                return True
            if curr - start >= wait_time:
                break
        return False

    def run(self, once=True):
        if not self._wait_to_run():
            self.stop()
            return
        self.running = True
        self.run_heart_beat()

        try:
            self.worker_run()
        except Exception as e:
            self.stop()
            return

        if once:
            self.stop()

    def stop(self):
        self.running = False
        self.stop_heart_beat()

    def worker_run(self):
        pass


class ModelTrainWorker:

    def __init__(self, worker_id, hb_time=60000):
        super(ModelTrainWorker, self).__init__(worker_id, hb_time)
        self._wait = Event()
        self._scheduled = None

    def worker_run(self):
        self._ev.wait()
        if self._scheduled:
            self._scheduled()

    def train_model(self, model_name, train_data, model_version=None):
        self._scheduled = lambda: self.do_train_model(model_name, train_data, model_version=None)
        self._wait.set()

    def do_train_model(self, model_name, train_data, model_version=None):
        pass
