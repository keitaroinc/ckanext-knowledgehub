import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import url
from sqlalchemy.exc import (ProgrammingError, IntegrityError,
                            DBAPIError, DataError)

import ckan.plugins.toolkit as toolkit
from ckan import lib
import ckan.logic as logic
from ckan.common import _

import ckanext.datastore.helpers as datastore_helpers
from ckanext.knowledgehub.backend import Backend
from ckanext.knowledgehub.backend import schema as backend_schema

log = logging.getLogger(__name__)

_df = lib.navl.dictization_functions
ValidationError = toolkit.ValidationError

is_single_statement = datastore_helpers.is_single_statement

_TIMEOUT = 10  # seconds
_DATE_FORMATS = ['%Y-%m-%d',
                 '%Y-%m-%d %H:%M:%S',
                 '%Y-%m-%dT%H:%M:%S',
                 '%Y-%m-%dT%H:%M:%SZ',
                 '%d/%m/%Y',
                 '%m/%d/%Y',
                 '%d-%m-%Y',
                 '%m-%d-%Y']


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
            table_row[field['id']] = row[field['id']]
        records.append(table_row)

    data['records'] = records
    data['fields'] = fields

    return data


class MssqlBackend(Backend):

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if not self._engine:
            self._engine = \
                create_engine(
                    self.read_url,
                    connect_args={'timeout': _TIMEOUT})
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

        data, errors = _df.validate(config, backend_schema.mssql(), {})
        if errors:
            raise ValidationError(errors)
        else:
            # We don't want to store DB password for now
            config.pop('password', None)

        # check for required connection parameters
        host = data.get('host')
        port = data.get('port')
        username = data.get('username')
        password = data.get('password')
        database = data.get('db_name')

        kwargs = {
            'drivername': 'mssql+pymssql',
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

        sql = toolkit.get_or_bust(data_dict, 'sql')

        if not is_single_statement(sql):
            raise toolkit.ValidationError({
                'sql': [_('SQL Query is not a single statement.')]
            })

        try:
            engine = self._get_engine()
            connection = engine.connect()
        except Exception as e:
            log.error(e)
            raise logic.ValidationError({
                'connection_parameters':
                [_('Unable to connect to Database, please check!')]
            })

        try:
            results = connection.execute(sql)
            return format_results(results)
        except ProgrammingError as e:
            log.error(e)
            raise ValidationError({
                'Error': [_('Please check the SQL!')]
            })
        except DBAPIError as e:
            log.error(e)
            raise ValidationError({
                'DB_API_Error': [_('Please check the SQL!')]
            })
        finally:
            connection.close()
