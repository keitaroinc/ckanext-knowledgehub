# -*- coding: utf-8 -*-
class Backend:

    def configure(self, config):
        """Configure backend, set inner variables,
         make the initial setup.

        :param config: configuration object
        :returns: config

        """
        return config

    def search_sql(self, context, data_dict):
        """Advanced search.

        :param sql: a single search statement
        :type sql: string

        :rtype: dictionary
        :param fields: fields/columns and their extra metadata
        :type fields: list of dictionaries
        :param records: list of matching results
        :type records: list of dictionaries
        """
        raise NotImplementedError()
