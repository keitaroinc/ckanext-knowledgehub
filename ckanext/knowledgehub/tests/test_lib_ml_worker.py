"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from mock import Mock, patch, MagicMock
from threading import Thread, RLock, Event
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


class Expect(Thread):

    def __init__(self, assertions):
        super(Expect, self).__init__(name='Expect')
        self.assertions = assertions
        self.values = {}
        self.event = Event()

    def run(self):
        while True:
            self.event.wait(0.1)
            all_accepted = True
            for name, expected in self.assertions.items():
                value = self.values.get(name)
                if value != expected:
                    all_accepted = False
                    break
            if all_accepted:
                break

    def set_value(self, name, value):
        self.values[name] = value
        self.event.set()


class TestWorker(helpers.FunctionalTestBase):

    def test_run_worker(self):
        redis_mock = MagicMock()
        expect = Expect({
            'setex': 1,
            'delete': 1,
        })

        redis_mock.get.return_value = None
        redis_mock.setex.side_effect = lambda *a, **kw: expect.set_value(
            'setex', 1)
        redis_mock.delete.side_effect = lambda *a, **kw: expect.set_value(
            'delete', 1)

        expect.start()

        worker = Worker('test_worker', 100000, redis=redis_mock)
        worker.run()

        expect.join(timeout=30)
        redis_mock.setex.assert_called_once_with(
            'ckan:worker:test_worker:heartbeat', 'RUNNING', 101)
        redis_mock.delete.assert_called_once()

    def test_run_worker_heartbeat(self):
        redis_mock = MagicMock()
        expect = Expect({
            'setex': 2,
            'delete': 1,
        })
        counts = {
            'setex': 0,
            'delete': 0,
        }

        def _get_and_increment(name):
            value = counts[name] + 1
            counts[name] = value
            expect.set_value(name, value)
            return value

        redis_mock.get.return_value = None
        redis_mock.setex.side_effect = lambda *a, **kw: \
            _get_and_increment('setex')
        redis_mock.delete.side_effect = lambda *a, **kw: \
            _get_and_increment('delete')

        expect.start()

        class _worker(Worker):

            def worker_run(self):
                from time import sleep
                sleep(0.5)

        worker = _worker('test_worker', 400, redis=redis_mock)
        worker.run()

        expect.join(timeout=30)

        redis_mock.setex.assert_called_with(
            'ckan:worker:test_worker:heartbeat', 'RUNNING', 1)
        assert_equals(redis_mock.setex.call_count, 2)
        redis_mock.delete.assert_called_once()


class TestModelTrainWorker(helpers.FunctionalTestBase):

    def test_run_train_model(self):
        redis_mock = MagicMock()

        redis_mock.get.return_value = None

        train_worker = ModelTrainWorker('test_ml_train', 1000)

        train_worker.do_train_model = Mock()

        train_worker.train_model('test-model', 'test-dataset', '0.1.1')

        train_worker.run()

        train_worker.do_train_model.assert_called_once_with(
            'test-model', 'test-dataset', '0.1.1')
