class NLPProcessor:

    def extract_entities(self, text):
        pass

    def generate_sentence(self, entities, grammar=None):
        pass





# Export default instances
_nlp_processor = NLPProcessor()

def get_nlp_processor():
    return _nlp_processor