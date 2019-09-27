#!/bin/bash
set -e

echo "This is travis-build.bash..."

echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install solr-jetty

echo "Installing CKAN and its Python dependencies..."
git clone https://github.com/ckan/ckan
cd ckan
git checkout "ckan-2.8.2"
python setup.py develop
# Travis has an issue with older version of psycopg2 (2.4.5)
sed -i 's/psycopg2==2.4.5/psycopg2==2.7.3.2/' requirements.txt
pip install -r requirements.txt 
pip install -r dev-requirements.txt
cd -

echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'
sudo -u postgres psql -c "CREATE USER datastore_default WITH PASSWORD 'ckan_default';"
sudo -u postgres psql -c 'CREATE DATABASE datastore_test WITH OWNER datastore_default;'

echo "SOLR config..."
# Solr is multicore for tests on ckan master, but it's easier to run tests on
# Travis single-core. See https://github.com/ckan/ckan/issues/2972
sed -i -e 's/solr_url.*/solr_url = http:\/\/127.0.0.1:8983\/solr/' ckan/test-core.ini

echo "Initialising the database..."
cd ckan
paster db init -c test-core.ini
paster datastore set-permissions -c test-core.ini | sudo -u postgres psql
cd -

echo "Installing ckanext-knowledgehub and its requirements..."
python setup.py develop
pip install -r requirements.txt
pip install -r dev-requirements.txt

echo "Setup database tables for ckanext-knowledgehub"
knowledgehub -c ckan/test-core.ini db init

echo "Moving test.ini into a subdir..."
mkdir subdir
mv test.ini subdir

cd ..
echo "Installing ckanext-datapusher and it's requirements... "
git clone https://github.com/ckan/datapusher.git
cd datapusher
pip install -r requirements.txt
cd -

pip install SQLAlchemy==1.1.11
pip install vdm==0.14
#pip install flask==0.12
#pip install flask-login

#sudo -u postgres psql datastore_default -f ../ckanext-xloader/full_text_function.sql
#sudo -u postgres psql datastore_test -f ../ckanext-xloader/full_text_function.sql

#paster datastore set-permissions -c test-core.ini | sudo -u postgres psql

echo "travis-build.bash is done."
