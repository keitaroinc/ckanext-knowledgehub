import logging
import json
import datetime

from six import string_types, text_type

from sqlalchemy import create_engine
from sqlalchemy.engine import url
from sqlalchemy.exc import (ProgrammingError,
                            DBAPIError, OperationalError)

import ckan.plugins.toolkit as toolkit
from ckan.common import _

from ckanext.knowledgehub.backend import Backend

log = logging.getLogger(__name__)

ValidationError = toolkit.ValidationError

_TIMEOUT = 60000  # milliseconds

_PG_ERR_CODE = {
    'unique_violation': '23505',
    'query_canceled': '57014',
    'undefined_object': '42704',
    'syntax_error': '42601',
    'permission_denied': '42501',
    'duplicate_table': '42P07',
    'duplicate_alias': '42712',
}


def convert(data, type_name):
    if data is None:
        return None
    if type_name == 'nested':
        return json.loads(data[0])
    # array type
    if type_name.startswith('_'):
        sub_type = type_name[1:]
        return [convert(item, sub_type) for item in data]
    if type_name == 'tsvector':
        return text_type(data, 'utf-8')
    if isinstance(data, datetime.datetime):
        return data.isoformat()
    if isinstance(data, (int, float)):
        return data
    return text_type(data)


def format_results(results):
    data = {}

    fields = []
    for field in results.cursor.description:
        # TODO get correct type instead of type code
        fields.append({
            'id': field[0].decode('utf-8'),
            'type': field[1]
        })

    records = []
    for row in results:
        table_row = {}
        for field in fields:
            table_row[field['id']] = \
                convert(row[field['id']], '')
        records.append(table_row)

    data['records'] = records
    data['fields'] = fields

    return data


class PostgresqlBackend(Backend):

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if not self._engine:
            self._engine = \
                create_engine(self.read_url)
        return self._engine

    def configure(self, config):
        ''' Configures the backend engine,
        this method must be called before using the
        'search_sql' method in order to set up
         the backend instance

        :param host: database host parameter
        (required, e.g. 'localhost')
        :type host: string
        :param port: database port parameter
        (required, e.g. 1433)
        :type port: int
        :param username: database username
        (required, e.g. 'SA')
        :type username: string
        :param username: database password
        (required, e.g. 'password')
        :type username: string
        :param username: database name
        (required, e.g. 'test_database')
        :type username: string
        '''

        # check for required connection parameters
        host = toolkit.get_or_bust(config, 'host')
        port = toolkit.get_or_bust(config, 'port')
        username = toolkit.get_or_bust(config, 'username')
        password = toolkit.get_or_bust(config, 'password')
        database = toolkit.get_or_bust(config, 'db_name')

        kwargs = {
            'drivername': 'postgresql',
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'database': database
        }
        # set the connection url for the
        # appropriate engine type
        self.read_url = url.URL(**kwargs)

    def search_sql(self, data_dict):
        '''
        :param sql: the sql statement that will be
        executed against the previously configured backend
         (required, e.g. 'SELECT * FROM table_name')

        :rtype: dictionary
        :param fields: fields/columns and their extra metadata
        :type fields: list of dictionaries
        :param records: list of matching results
        :type records: list of dictionaries
        '''
        try:
            engine = self._get_engine()
            connection = engine.connect()
        except OperationalError as e:

            log.error(e)

            raise ValidationError({
                'connection_parameters':
                    [_('Unable to connect to Database, please check!')]
            })

        sql = data_dict['sql']

        try:
            connection.execute(
                u'SET LOCAL statement_timeout TO {0}'.format(_TIMEOUT))

            results = connection.execute(sql)

            return format_results(results)

        except ProgrammingError as e:
            if e.orig.pgcode == _PG_ERR_CODE['permission_denied']:
                raise toolkit.NotAuthorized({
                    'permissions': ['Not authorized to read resource.']
                })

            def _remove_explain(msg):
                return (msg.replace('EXPLAIN (VERBOSE, FORMAT JSON) ', '')
                        .replace('EXPLAIN ', ''))

            raise ValidationError({
                'query': [_remove_explain(str(e))],
                'info': {
                    'statement': [_remove_explain(e.statement)],
                    'params': [e.params],
                    'orig': [_remove_explain(str(e.orig))]
                }
            })
        except DBAPIError as e:
            if e.orig.pgcode == _PG_ERR_CODE['query_canceled']:
                raise ValidationError({
                    'query': ['Query took too long']
                })
            raise
        finally:
            connection.close()
