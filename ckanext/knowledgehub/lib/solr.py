import hashlib
from uuid import uuid4
from ckan.common import config
from ckan.lib.search.common import make_connection
from logging import getLogger



logger = getLogger(__name__)


FIELD_PREFIX = 'khe_'
COMMON_FIELDS = {'name', 'title'}
CHUNK_SIZE = 1000


def _prepare_search_query(query):
    def _to_pysolr_arg(value):
        if isinstance(value, str) or isinstance(value, unicode):
            return [value]
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            val = []
            for k,v in value.items():
                val.append(str(k) + ':' + str(v))
            return val
        return [str(value)]
    if not query.get('fq'):
        query['fq'] = []
    query['fq'] = _to_pysolr_arg(query['fq'])
    
    return query

class Index:

    def get_connection(self):
        return make_connection()

    def _to_solr_args(self, doctype, query):
        solr_args = {}
        solr_args.update(query)
        solr_args = _prepare_search_query(solr_args)
        solr_args['fq'].append('entity_type:'+doctype)
        logger.debug('Solr query args: %s', solr_args)
        return solr_args

    def search(self, doctype, **query):
        return self.get_connection().search(**self._to_solr_args(doctype, query))

    def add(self, doctype, data):
        solr_data = {}
        solr_data.update(data)
        solr_data['entity_type'] = doctype
        self.get_connection().add([solr_data], commit=True)

    def update(self, doctype, data):
        pass

    def remove(self, doctype, **query):
        q = 'entity_type:' + doctype
        additional_args = []
        for key,value in query.items():
            additional_args.append('%s:%s' % (key, value))
        if additional_args:
            q += ' AND ' + ' AND '.join(additional_args)
        logger.debug('Delete documents q=%s', q)
        self.get_connection().delete(commit=True, q=q)

    def remove_all(self, doctype):
        self.get_connection().delete(commit=True, q='entity_type:' + doctype)

# Exported
index = Index()


# Helpers for models

def mapped(name, _as):
    u'''Map the field name of the model to a specific name in the index.
    '''
    return {
        'field': name,
        'as': _as
    }

def unprefixed(name):
    u'''Use the name of the field as it is, i.e don't prefix this name in the
    index even it is not a common field.
    '''
    return mapped(name, name)


def _get_fields_mapping(fields):
    mapping = {}
    for field in fields:
        key, _as = None, None
        explicit_name = False
        if isinstance(field, dict):
            key = field['field']
            _as = field['as']
            explicit_name = True
        else:
            key, _as = field, field
        
        if key not in COMMON_FIELDS and not explicit_name:
            _as = FIELD_PREFIX + _as
        mapping[key] = _as
    return mapping

def _add_required_fields(data):
    if not data.get('id'):
        data['id'] = str(uuid4())
    if not data.get('site_id'):
        data['site_id'] = config.get('ckan.site_id')
    if not data.get('index_id'):
        entity_id = data.get('entity_id', data['id'])
        doctype = data['entity_type']
        data['index_id'] = hashlib.md5('%s:%s'%(doctype, entity_id)).hexdigest()
    return data

def to_indexed_doc(data, doctype, fields):
    indexed_doc = {
        'entity_type': doctype,
    }
    for name, index_field in _get_fields_mapping(fields).items():
        if data.get(name):
            indexed_doc[index_field] = data[name]

    return _add_required_fields(indexed_doc)

def indexed_doc_to_data_dict(doc, fields):
    data = {}
    for name, index_field in _get_fields_mapping(fields).items():
        if doc.get(index_field):
            data[name] = doc[index_field]

    return data


# Mixin
class Indexed:

    @classmethod
    def _get_indexed_fields(cls):
        if hasattr(cls, 'indexed'):
            return cls.indexed
        return [field for field in COMMON_FIELDS]

    @classmethod
    def _get_doctype(cls):
        if hasattr(cls, 'doctype'):
            return cls.doctype
        raise Exception('Doctype for %s is missing. Please define a doctype for this model.' % cls)

    @classmethod
    def _get_session(cls):
        if hasattr(cls, 'Session'):
            return cls.Session
        raise Exception('Session not defined for this model repository.')

    @classmethod
    def _get_before_index(cls):
        if hasattr(cls, 'before_index'):
            return cls.before_index
        def _noop(data):
            return data
        return _noop

    @classmethod
    def rebuild_index(cls):
        fields = cls._get_indexed_fields()
        doctype = cls._get_doctype()
        error = False
        def _generate_index():
            offset = 0
            def _next_chunk():
                count = 0
                for result in cls._get_session().query(cls).offset(offset).limit(CHUNK_SIZE).all():
                    try:
                        data = cls._get_before_index()(result.__dict__)
                        index.add(doctype, to_indexed_doc(data, doctype, fields))
                    except Exception as e:
                        logger.exception(e)
                        logger.error('Failed to build index for: %s. Error: %s', result, e)
                        error = True
                    count += 1
                return count
            
            while True:
                count  = _next_chunk()
                if not count:
                    break
                offset += CHUNK_SIZE
            
        
        # clear all documents of this type from the index
        index.remove_all(doctype)
        # now regenerate the index
        _generate_index()
        if error:
            logger.error('Rebuilding of index for %s finished with error. Check the log for more details.', doctype)
        logger.info('Rebuilt index for %s.', doctype)

    @classmethod
    def add_to_index(cls, data):
        doctype = cls._get_doctype()
        fields  =cls._get_indexed_fields()
        doc = to_indexed_doc(cls._get_before_index()(data), doctype, fields)
        index.add(cls._get_doctype(), doc)
    
    @classmethod
    def update_index_doc(cls, data):
        fields = cls._get_indexed_fields()
        fields_mapping = _get_fields_mapping(fields)
        entity_id = data['id']
        id_key = fields_mapping.get('id', 'id')
        indexed = index.search(cls._get_doctype(), q='%s:%s' % (id_key, entity_id))
        doc = None
        for d in indexed:
            doc = d
            break
        if doc:
            index.remove(cls._get_doctype(), id=doc['id'])
        index.add(cls._get_doctype(), to_indexed_doc(cls._get_before_index()(data), cls._get_doctype(), fields))

    @classmethod
    def search_index(cls, **query):
        index_results = index.search(cls._get_doctype(), **query)
        results = []
        fields = cls._get_indexed_fields()

        for result in index_results:
            results.append(indexed_doc_to_data_dict(result, fields))

        return results
    
    @classmethod
    def delete_from_index(cls, data):
        doc_id = None
        if isinstance(data, str) or isinstance(data, unicode):
            doc_id = data
        else:
            doc_id = data['id']
        doctype = cls._get_doctype()
        fields_mapping = _get_fields_mapping(cls._get_indexed_fields())
        id_key = fields_mapping.get('id', 'id')
        args = {}
        args[id_key] = doc_id
        index.remove(doctype, **args)
