from mock import Mock, patch, MagicMock

from ckan.tests import helpers

from ckanext.knowledgehub.lib.ml.worker import (
    Worker,
    ModelTrainWorker,
)

from nose.tools import (
    assert_true,
    assert_equals,
    raises,
)

class TestWorker(helpers.FunctionalTestBase):

    def test_run_worker(self):
        redis_mock = MagicMock()

        redis_mock.get.return_value = None

        worker = Worker('test_worker', 100000, redis=redis_mock)
        worker.run()

        from time import sleep
        sleep(2)

        redis_mock.setex.assert_called_once_with('ckan:worker:test_worker:heartbeat', 'RUNNING', 101)
        redis_mock.delete.assert_called_once()

    def test_run_worker_heartbeat(self):
        redis_mock = MagicMock()

        redis_mock.get.return_value = None

        class _worker(Worker):
            
            def worker_run(self):
                from time import sleep
                sleep(0.5)

        worker = _worker('test_worker', 400, redis=redis_mock)
        worker.run()

        redis_mock.setex.assert_called_with('ckan:worker:test_worker:heartbeat', 'RUNNING', 1)
        assert_equals(redis_mock.setex.call_count, 2)
        redis_mock.delete.assert_called_once()


class TestModelTrainWorker(helpers.FunctionalTestBase):

    def test_run_train_model(self):
        redis_mock = MagicMock()

        redis_mock.get.return_value = None
        
        train_worker = ModelTrainWorker('test_ml_train', 1000)

        train_worker.do_train_model = Mock()

        train_worker.train_model('test-model','test-dataset','0.1.1')

        train_worker.run()

        train_worker.do_train_model.assert_called_once_with('test-model','test-dataset','0.1.1')