# -*- coding: utf-8 -*-
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
