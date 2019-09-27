#!/bin/sh -e

echo "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty8
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo service jetty8 restart
# cd ..
# cd datapusher
# pip list
# #python datapusher/main.py deployment/datapusher_settings.py &

# cd -  
# cd ckanext-knowledgehub

nosetests --ckan \
          --nologcapture \
          --with-pylons=subdir/test.ini \
          --with-coverage \
          --cover-package=ckanext.knowledgehub \
          --cover-inclusive \
          --cover-erase \
          --cover-tests 
        #   -w ckanext/knowledgehub/tests

