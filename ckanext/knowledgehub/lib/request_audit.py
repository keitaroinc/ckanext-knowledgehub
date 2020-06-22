'''Implements a queued mechanism for saving log of all requests comming to the
site.

'''
import atexit
from threading import Thread, Event, RLock
from Queue import Queue
from logging import getLogger

from ckanext.knowledgehub.model import RequestAudit as RequestAuditModel


log = getLogger(__name__)
QUEUE_SIZE = 10000
WAIT_TIME = 0.1
BULK_SIZE = 1024


class RequestAudit:
    '''Request Audit service that uses a queue to buffer incoming requests and
    stores the log entries in the database in bulks.
    This service offloads the storing of the log entries in a separate thread.
    Every incoming log entry is stored asynchronously in a Queue, to be later
    consumed in the consumer thread and stored in the database.

    The worker thread consumes log entries periodically from the queue and
    stores them using a bulk operation.

    :param maxsize: `int`, maximal size of the queue.
    :param wait_time: `float`, wait time of the worker thread - time between
        storing bulk of entries in database.
    :param bulk_size: `int`, maximal number of entries to be stored in the DB
        at a time.
    '''
    def __init__(self,
                 maxsize=QUEUE_SIZE,
                 wait_time=WAIT_TIME,
                 bulk_size=BULK_SIZE):
        self.wait_time = wait_time
        self.bulk_size = bulk_size
        self.queue = Queue(maxsize=maxsize)
        self.worker_shutdown = Event()

        Thread(target=self._worker).start()
        atexit.register(self.shutdown)
        log.info('RequestAudit initialized. '
                 'Queue size=%d, wait time=%fs, bulk size=%d',
                 maxsize,
                 wait_time,
                 bulk_size)

    def _worker(self):
        log.info('RequestAudit logger started.')
        while not self.worker_shutdown.wait(self.wait_time):
            self._write_audit()
        log.info('RequestAudit logger worker shutdown.')

    def _write_audit(self):
        bulk = []
        while not self.queue.empty() and len(bulk) < self.bulk_size:
            audit_log = self.queue.get()
            request_audit = RequestAuditModel(
                remote_ip=audit_log.get('remote_ip'),
                remote_user=audit_log.get('remote_user'),
                session=audit_log.get('session'),
                current_language=audit_log.get('current_language'),
                access_time=audit_log.get('access_time'),
                request_url=audit_log.get('request_url'),
                http_method=audit_log.get('http_method'),
                http_path=audit_log.get('http_path'),
                http_query_params=audit_log.get('http_query_params'),
                http_user_agent=audit_log.get('http_user_agent'),
                client_os=audit_log.get('client_os'),
                client_device=audit_log.get('client_device'),
            )
            bulk.append(request_audit)

        if bulk:
            RequestAuditModel.insert_bulk(bulk)
            log.debug('Inserted %d audit log entries.', len(bulk))

    def log(self, data):
        '''Write a log entry.

        This operation is asynchronous, it just puts the `data` on the queue to
        be consumed later by the worker thread.

        :param data: `dict`, the log entry.
        '''
        try:
            self.queue.put_nowait(data)
        except Exception as e:
            # queue full
            log.exception(e)

    def shutdown(self):
        '''Shuts down the background thread and closes this service.
        '''
        self.worker_shutdown.set()
        log.info('Shutting down RequestAudit logger...')


_request_audit = None
_lock = RLock()


def get_request_audit():
    '''Returns a singleton instance of `RequestAudit`.
    '''
    global _request_audit
    if not _request_audit:
        with _lock:
            if not _request_audit:
                _request_audit = RequestAudit()
    return _request_audit
