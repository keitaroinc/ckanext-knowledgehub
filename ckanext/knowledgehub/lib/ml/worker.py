from logging import getLogger

class ModelTrainWorker:

    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.logger = getLogger('ModelTrainWorker:' + worker_id)

    def train_model(self, model_name, train_data, model_version=None):
        pass
