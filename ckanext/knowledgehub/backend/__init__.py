"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

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
