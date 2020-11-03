import hashlib
from uuid import uuid4
from ckan.common import config, _ as translate
from ckan.lib.search.common import make_connection
from ckan.plugins.toolkit import ValidationError
from logging import getLogger


logger = getLogger(__name__)


FIELD_PREFIX = 'khe_'
COMMON_FIELDS = {'name', 'title'}
CHUNK_SIZE = 1000
MAX_RESULTS = 500
VALID_SOLR_ARGS = {'q', 'fq', 'rows', 'start', 'sort', 'fl', 'df', 'facet',
                   'bq', 'defType', 'boost', 'facet.field'}
DEFAULT_FACET_NAMES = u'organizations groups tags'


class DontIndexException(Exception):
    u'''Flag exception to signal the indexer that it should not index this
    entity.
    '''
    pass


def _prepare_search_query(query):
    u'''Prepares the query parameters to be send to pysolr as function
    arguments.
    '''
    def _to_pysolr_arg(value):
        if isinstance(value, str) or isinstance(value, unicode):
            return [value]
        if isinstance(value, list):
            return sorted(value)
        if isinstance(value, dict):
            val = []
            for k, v in value.items():
                val.append(str(k) + ':' + str(v))
            return sorted(val)
        return [str(value)]

    if not query.get('fq'):
        query['fq'] = []
    query['fq'] = _to_pysolr_arg(query['fq'])

    # remove quotes from query to avoid literal searches
    # i.e. text:"trends funding" -> text:trends funding
    q = query.pop('q', 'text:*')
    q = q.replace('"', '')
    query['q'] = q

    return query


def escape_str(s):
    if not s:
        return s
    s = s.strip()
    if s == '*':
        return s
    s = s.replace('"', '\\"')
    return '"%s"' % s


def ckan_params_to_solr_args(data_dict):
    u'''Transforms the parameters parsed by CKAN as data dict to the
    appropriate (py)solr query arguments.

    Every entry in the dictionary will be validated and transformed to a solr
    arguments. Valid argument names are 'q', 'fq', 'rows', 'start', 'sort',
    'fl' and 'df'.

    A `ValidationError` will be raised if the data dict contains arguments that
    are not valid.

    :param data_dict: ``dict``, CKAN parameters as dictionary.

    :returns: ``dict`` with the transformed arguments valid for `pysolr`.
    '''
    solr_args = {}
    provided = {}
    provided.update(data_dict)
    facets = {}
    for argn in VALID_SOLR_ARGS:
        if provided.get(argn) is not None:
            if argn == 'facet.field':
                facets['facet.field'] = provided.pop(argn)
            else:
                solr_args[argn] = provided.pop(argn)

    q = []
    if solr_args.get('q'):
        _q = solr_args.get('q')
        if isinstance(_q, str) or isinstance(_q, unicode):
            q.append(escape_str(_q))
        elif isinstance(_q, dict):
            for prop, val in _q.items():
                q.append('%s:%s' % (str(prop), escape_str(str(val))))
        else:
            raise ValidationError({'q': _('Invalid value type')})

    for prop, val in provided.items():
        q.append('%s:%s' % (str(prop), escape_str(str(val))))

    solr_args['q'] = ' AND '.join(sorted(q))
    if facets:
        solr_args.update(facets)
    return solr_args


class Index:
    u'''Index is an abstraction over the raw indexer connection provided by
    CKAN.

    It takes into consideration the document type because the extra entities
    that are indexed in Solr are recorded as a separate document type (instead
    of the standard CKAN's `entity_type=package`).
    '''
    def get_connection(self):
        u'''Creates new raw connection to Solr.
        '''
        return make_connection()

    def _to_solr_args(self, doctype, query):
        solr_args = {}
        solr_args.update(query)
        solr_args = _prepare_search_query(solr_args)
        solr_args['fq'].append('entity_type:'+doctype)
        facet = solr_args.pop('facet', None)
        if facet:
            solr_args['facet'] = 'true'
            if not solr_args.get('facet.field'):
                solr_args['facet.field'] = config.get(
                    u'knowledgehub.search.facets', DEFAULT_FACET_NAMES).split()

        logger.debug('Solr query args: %s', solr_args)
        return solr_args

    def search(self, doctype, **query):
        u'''Performs search through the index for the given document type.

        :param doctype: ``str``, the document type to search for.
        :param query: ``dict`` or kwargs, extra parameters to be passed down to
            Solr. The parameter `rows` is implicitly added of not provided to
            limit the number of returned rows.
        '''
        if not query.get('rows'):
            query['rows'] = MAX_RESULTS
        if int(query['rows']) > MAX_RESULTS:
            query['rows'] = MAX_RESULTS
        return self.get_connection().search(
            **self._to_solr_args(doctype, query))

    def add(self, doctype, data):
        u'''Adds new document to the index with the given document type.

        An additional property in the document called ``entity_type`` is added
        to store the document type.

        :param doctype: ``str``, the document type.
        :param data: ``dict``, the document data.
        '''
        solr_data = {}
        solr_data.update(data)
        solr_data['entity_type'] = doctype
        self.get_connection().add([solr_data], commit=True)

    def remove(self, doctype, **query):
        u'''Removes documents from the index for the given document type.

        Additional query filters may be added as kwargs to the method to narrow
        down the selection of documents to be deleted.

        :param doctype: ``str``, the document type.
        :param query: ``dict`` as kwargs, additional selection arguments to
            narrow down the selection of documents to be deleted.
        '''
        q = 'entity_type:' + doctype
        additional_args = []
        for key, value in query.items():
            additional_args.append('%s:%s' % (key, value))
        if additional_args:
            q += ' AND ' + ' AND '.join(sorted(additional_args))
        logger.debug('Delete documents q=%s', q)
        self.get_connection().delete(commit=True, q=q)

    def remove_all(self, doctype):
        u'''Removes all documents from the index for the given document type.

        :param doctype: ``str``, the document type.
        '''
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
        data['index_id'] = hashlib.md5(
            '%s:%s' % (doctype, entity_id)).hexdigest()
    return data


def to_indexed_doc(data, doctype, fields):
    u'''Maps raw document data to a document that will be stored in the index.

    The mapping is done based on the provided fields definitions. The indexed
    document will contain only the fields that are specified. If the original
    document contains more data (additional properties) that are not specified
    they will be ignored and not stored in the index.

    A field definition can be ordinary string - the name of the property to be
    stored. For finer controll over how to store the property in the index, a
    dict can be provided with the following structure:

        .. code-block:: python

            {
                "field": "field_name",
                "as": "stored_field_name"
            }

    Additional fields that are required by Solr index will be added to the
    document if they are not present. Required fields are: `id`, `site_id` and
    `index_id`.
    The field `entity_type` is added to all documents.

    An example of field mapping:

        .. code-block:: python

            # field mappings
            fields = [
                {'field': 'id', 'as': 'id'}, # or use mapped('id', 'id')
                'name',
                'title',
                'description']

            # original document
            data = {
                'id': 'id-1',
                'name': 'first-document',
                'title': 'First Document',
                'description': 'Document example',
                'additional': 'Additional value that will be ignored',
            }

            # map to indexed document
            doc = to_indexed_doc(data, 'test_doc', fields)

            # The doc will look like this:
            {
                "id": "id-1",
                "index_id": "<generated_value>",
                "site_id": "default.site.id",
                "entity_type": "test_doc",
                "name": "first-document",  # this is a common field, no prefix
                "title": "First Document", # also a common field, no prefix
                "khe_description": "Document Example", # prefixed
            }
            # note that the property 'additional' is not present as it is not
            # in the fields mappings and should not be indexed.

    :param data: ``dict``, the original document to be stored in the index.
    :param doctype: ``str``, the document type.
    :param fields: ``list``, fields mapping.

    :returns: ``dict``, the mapped document ready to be stored in the index.
    '''
    indexed_doc = {
        'entity_type': doctype,
    }
    for name, index_field in _get_fields_mapping(fields).items():
        if data.get(name):
            indexed_doc[index_field] = data[name]

    return _add_required_fields(indexed_doc)


def indexed_doc_to_data_dict(doc, fields):
    u'''Mapps a document fetched from the index, to a document with the
    original structure based on the fields mappings.

    This function basically does the reverse process of `to_indexed_doc`.

    :param doc: ``dict``, document as fetched from the index.
    :param fields: ``list``, the fields mappings.

    :returns: ``dict``, a document, mapped to the original structure.
    '''
    data = {}
    for name, index_field in _get_fields_mapping(fields).items():
        if doc.get(index_field):
            data[name] = doc[index_field]

    return data


# Mixin
class Indexed:
    u'''Mixin that adds indexing capabilities to a defined Model.

    Given a model repository class, this mixin can be added to give
    capabilities to the model to store, update, delete, search and rebuild the
    index for the given model entity in the Solr index.

    The class that is enriched with this mixin can provide the following
    static propeties to controll the behaviour of the index actions:

        * `indexed - ``list`` of field mappings that specify which fields of
            the model we want to index. If not specified, only the
            COMMON_FIELDS will be indexed.
        * `doctype` - ``str``, required, the document type name for this model.
            If not given, an error will be raised.
        * `index` - ``Index``, optional, the instance of the ``Index`` to be
            used. Usefull for providing mock index in unit tests.
        * `before_index` - `function`, optional, a callback function that is
            called before the entity is stored in the index to provide a way to
            modify, transform, validate or enrich the data before it goes in
            the index.
            The method signature for this callback is:

                .. code-block:: python

                    def before_index(data):
                        return data

            The callback receives the document data (as ``dict``) and expects a
            ``dict`` as a return value - the transformed document.

    A usage example:

        .. code-block:: python

            class MyModel(DomainObject, Indexed):

                indexed = [
                    unprefixed('id'), # use id without prefix
                    'name',
                    'title',
                    'description',
                    'tags',
                ]
                doctype = 'my_model'

                @classmethod
                def before_index(cls, data):
                    # called before the data goes into the index
                    # does some transformation and returns the transformed dict
                    data['extras_data'] = 'extra data'
                    return data

                # additional methods bellow...

    '''
    @classmethod
    def get_index(cls):
        u'''Returns a reference to the ``Index`` to be used with this mixin.

        Usefull if you need to provide other instance of the Index or to
        provide a mock implementation in unit tests.
        '''
        if hasattr(cls, 'index'):
            return cls.index
        return index

    @classmethod
    def _get_indexed_fields(cls):
        if hasattr(cls, 'indexed'):
            return cls.indexed
        return [field for field in COMMON_FIELDS]

    @classmethod
    def _get_doctype(cls):
        if hasattr(cls, 'doctype'):
            return cls.doctype
        raise Exception('Doctype for %s is missing. ' +
                        'Please define a doctype for this model.' % cls)

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
        u'''Performs a full rebuild of the index for the documents of this
        type.

        It collects the data from the database for this model, transforms and
        inserts the documents into the index. First all documents of this type
        are deleted in the index (to clean-up stale documents), then all of the
        documents are collected from database and re-instered into the index.
        '''
        index = cls.get_index()
        fields = cls._get_indexed_fields()
        doctype = cls._get_doctype()
        error = False

        def _generate_index():
            offset = 0

            def _next_chunk():
                count = 0
                for result in (cls._get_session()
                               .query(cls)
                               .offset(offset)
                               .limit(CHUNK_SIZE)
                               .all()):
                    try:
                        data = cls._get_before_index()(result.__dict__)
                        index.add(doctype,
                                  to_indexed_doc(data, doctype, fields))
                    except DontIndexException as e:
                        logger.debug('Should not index this resource %s.',
                                     str(e))
                    except Exception as e:
                        logger.exception(e)
                        logger.error('Failed to build index for %s. Error: %s',
                                     result,
                                     e)
                        error = True
                    count += 1
                return count

            while True:
                count = _next_chunk()
                if not count:
                    break
                offset += CHUNK_SIZE

        # clear all documents of this type from the index
        index.remove_all(doctype)
        # now regenerate the index
        _generate_index()
        if error:
            logger.error('Rebuilding of index for %s finished with error. ' +
                         'Check the log for more details.', doctype)
        logger.info('Rebuilt index for %s.', doctype)

    @classmethod
    def add_to_index(cls, data):
        u'''Adds new document to the index.

        :param data: ``dict``, the document data.
        '''
        doctype = cls._get_doctype()
        fields = cls._get_indexed_fields()
        try:
            doc = to_indexed_doc(cls._get_before_index()(data),
                                 doctype, fields)
            cls.get_index().add(cls._get_doctype(), doc)
        except DontIndexException as e:
            logger.debug('Signaled to not index this resource %s.', str(e))

    @classmethod
    def update_index_doc(cls, data):
        u'''Updates an exiting document in the index.

        :param data: ``dict``, the document to be updated. It must contain an
            `id` so the system can locate and update the document in the index.
        '''
        index = cls.get_index()
        fields = cls._get_indexed_fields()
        fields_mapping = _get_fields_mapping(fields)
        entity_id = data['id']
        id_key = fields_mapping.get('id', 'id')
        indexed = index.search(cls._get_doctype(),
                               q='%s:%s' % (id_key, entity_id))
        doc = None
        for d in indexed:
            doc = d
            break
        if doc:
            idarg = {id_key: doc[id_key]}
            index.remove(cls._get_doctype(), **idarg)
        try:
            index.add(cls._get_doctype(),
                      to_indexed_doc(
                        cls._get_before_index()(data),
                        cls._get_doctype(),
                        fields
                      ))
        except DontIndexException as e:
            logger.debug('Signaled to not index this resource %s.', str(e))

    @staticmethod
    def validate_solr_args(args):
        u'''Validates the arguments for usage in Solr.
        '''
        msg = {}
        for argn, _ in args.items():
            if argn not in VALID_SOLR_ARGS:
                msg[argn] = translate('Invalid parameter')
        if len(msg):
            raise ValidationError(msg)

    @classmethod
    def search_index(cls, **query):
        u'''Performs a search in the index for documents of this type.

        The query arguments are going to be translated into valid Solr query
        parameters.
        '''

        if query.get('boost_for'):
            # Delay the loading of the user_profile service
            from ckanext.knowledgehub.lib.profile import user_profile_service
            user_id = query.pop('boost_for')
            boost_values = user_profile_service.get_interests_boost(user_id)
            boost_params = boost_solr_params(boost_values)
            query.update(boost_params)

        Indexed.validate_solr_args(query)
        index_results = cls.get_index().search(cls._get_doctype(), **query)
        results = []
        fields = cls._get_indexed_fields()

        for result in index_results:
            results.append(indexed_doc_to_data_dict(result, fields))
        index_results.docs = results
        return index_results

    @classmethod
    def delete_from_index(cls, data):
        u'''Deletes a document from the index.

        :param data: ``dict``, must contain a valid `id` so the document can be
            located and deleted.
        '''
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
        cls.get_index().remove(doctype, **args)


def boost_solr_params(values):
    '''Transforms the values dict into edismax solr query arguments.
    '''

    if not values:
        return {}

    params = {
        'defType': 'edismax',
    }

    bq = []
    for prop, prop_values in values.get('normal', {}).items():
        for value in prop_values:
            bq.append("%s:%s" % (prop, value))

    for scale, boost_params in values.items():
        if scale == 'normal':
            continue
        for prop, prop_values in boost_params.items():
            for value in prop_values:
                bq.append("%s:%s%s" % (prop, value, scale))

    if bq:
        params['bq'] = ' + '.join(bq)
    return params


def get_fq_permission_labels(permission_labels):
    fq = '+permission_labels:'
    fq += '(' + ' OR '.join([escape_str(label) for label in
                            permission_labels]) + ')'
    return fq


def get_sort_string(model_cls, sort_str):
    sort_by = _parse_sort_str(sort_str)
    if not sort_by:
        return None
    mapping = _get_fields_mapping(model_cls.indexed)
    sort_expr = []
    for column, order in sort_by:
        column = mapping.get(column, column)
        sort_expr.append('%s %s' % (column, order))

    return ','.join(sort_expr)


def _parse_sort_str(sort_str):
    sort_by = []
    for sort_field in sort_str.strip().split(','):
        sort_field = sort_field.strip()
        if not sort_field:
            continue
        expr = list(filter(lambda exp: exp and exp.strip(),
                           sort_field.split()))
        column = expr[0]
        order = expr[1] if len(expr) > 1 else 'asc'
        sort_by.append((column, order))
    return sort_by
