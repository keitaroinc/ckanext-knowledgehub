# -*- coding: utf-8 -*-

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

import logging
import csv
import cStringIO

log = logging.getLogger(__name__)


class WriterService:
    def csv_writer(self, fields, records, delimiter):

        columns = [str(f['id']).encode("utf-8") for f in fields]
        output = cStringIO.StringIO()

        delimiter = str(delimiter).lower()
        if delimiter == 'semicolon':
            writer = csv.writer(output, delimiter=';')
        elif delimiter == 'pipe':
            writer = csv.writer(output, delimiter='|')
        elif delimiter == 'tab':
            writer = csv.writer(output, dialect='excel-tab')
        else:
            writer = csv.writer(output, delimiter=',')

        # Writing headers
        writer.writerow(columns)

        # Writing records
        for record in records:
            writer.writerow([record[column] for column in columns])

        file_content = cStringIO.StringIO(output.getvalue())
        output.close()

        return file_content
