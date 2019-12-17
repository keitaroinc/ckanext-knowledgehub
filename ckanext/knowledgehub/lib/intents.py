class UserIntentsExtractor:

    def extract_intents(self, query):
        pass


class UserIntentsWorker:

    def __init__(self, extractor):
        self.extractor = extractor
    
    def update_latest(self):
        pass

    def rebuild(self):
        pass