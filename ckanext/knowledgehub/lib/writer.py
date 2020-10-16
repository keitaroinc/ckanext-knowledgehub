# -*- coding: utf-8 -*-
import logging
import csv
import cStringIO

log = logging.getLogger(__name__)


class WriterService():

    def csv_writer(self, fields, records, delimiter):

        d = str(delimiter).lower()

        columns = [str(x['id']).encode("utf-8") for x in fields]
        output = cStringIO.StringIO()

        if d == 'semicolon':
            writer = csv.writer(output, delimiter=';')
        elif d == 'pipe':
            writer = csv.writer(output, delimiter='|')
        elif d == 'tab':
            writer = csv.writer(output, dialect='excel-tab')
        else:
            writer = csv.writer(output, delimiter=',')

        # Writing headers
        writer.writerow([str(f['id']).encode("utf-8") for f in fields])

        # Writing records
        for record in records:
            writer.writerow([record[column].encode("utf-8")
                            for column in columns])

        file_content = cStringIO.StringIO(output.getvalue())

        output.close()

        return file_content
