import logging
import sqlparse
import datetime
import json
import csv


from sqlalchemy import create_engine
from sqlalchemy.engine import url
from sqlalchemy.exc import (ProgrammingError, IntegrityError,
                            DBAPIError, DataError)
import ckan.plugins.toolkit as toolkit

import ckanext.datastore.helpers as datastore_helpers
from ckanext.knowledgehub.backend import Backend

log = logging.getLogger(__name__)

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

        # check for required connection parameters
        host = toolkit.get_or_bust(config, 'host')
        port = toolkit.get_or_bust(config, 'port')
        username = toolkit.get_or_bust(config, 'username')
        password = toolkit.get_or_bust(config, 'password')
        database = toolkit.get_or_bust(config, 'db_name')

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
                'query': ['Query is not a single statement.']
            })

        engine = self._get_engine()
        connection = engine.connect()

        try:
            # types = connection.execute("SELECT COLUMN_NAME, DATA_TYPE  "
            #                            "FROM INFORMATION_SCHEMA.COLUMNS"
            #                            " WHERE TABLE_NAME = 'Products'")
            results = connection.execute(sql)
            return format_results(results)
        except ProgrammingError as e:
            # TODO handle errors
            log.error(e)
            raise
        except DBAPIError as e:
            # TODO handle errors
            log.error(e)
            raise ValidationError(e)
        finally:
            connection.close()
