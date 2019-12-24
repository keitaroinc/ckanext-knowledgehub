class NLPProcessor:

    def extract_entities(self, text):
        pass

    def generate_sentence(self, entities, grammar=None):
        pass


class MLModel:
    
    def predict(self, inp):
        pass

    def train(self, data_set):
        pass

class ModelLocator:

    def get_model(self, name, version):
        # noop model, won't predict anything but lets the flow go through
        return MLModel() 


# Export default instances
_nlp_processor = NLPProcessor()


def get_nlp_processor():
    return _nlp_processor


model_locator = ModelLocator()