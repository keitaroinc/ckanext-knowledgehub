Installation Guide
==================

This installation guide assumes installing and deploying CKAN from source on
Ubuntu Server 18.04 and CentOS 7 (2003).

# Install CKAN

Full installation guide documentation is available on CKAN docs:
 * [Installing CKAN](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-source.html)
 * [Deployment](https://docs.ckan.org/en/2.8/maintaining/installing/deployment.html)

## 1. Install base packages

### Ubuntu Server 18.04
```bash
sudo apt install postgresql libpq-dev python-pip python-virtualenv git redis-server openjdk-8-jdk postgis
```

### CentoOS 7
```bash
sudo yum install -y python-devel postgresql-server postgresql-contrib python-pip python-virtualenv postgresql-devel git redis postgis wget lsof policycoreutils-python
```

Then initialize and start PostgreSQL database

```bash
sudo postgresql-setup initdb

sudo systemctl start postgresql

# Let it start always on system start
sudo systemctl enable postgresql
```


## 2. Create folder structure

First let's create a special user for CKAN:

```bash
sudo useradd -m -s /bin/bash ckan
```

Then switch to that user:

```bash
sudo -i -u ckan
```

And create the folders:

```bash
mkdir -p ~/ckan/lib
mkdir -p ~/ckan/etc
```

Exit to the user with sudo privileges, then create the necessary soft links:

```bash
sudo ln -s /home/ckan/ckan/lib /usr/lib/ckan
sudo ln -s /home/ckan/ckan/etc /etc/ckan
```

Create new Python virtualenv:

```bash
sudo mkdir -p /usr/lib/ckan/default
sudo chown ckan /usr/lib/ckan/default  # Important to make 'ckan' the owner of the virtualenv

# Then switch to 'ckan' user and create the virtualenv
sudo -i -u ckan
virtualenv --no-site-packages /usr/lib/ckan/default

```

Then activate the virtualenv. From this point on, make sure you have the virtualenv activated when executing the commands.
**Important Note**: Make sure you have activated the virutalenv with user **ckan**.

```bash
. /usr/lib/ckan/default/bin/activate
```

**CentOS 7**

Things are a bit different in CentOS. Here we will create a different user for ckan with home set to `/var/lib/ckan`. 


```bash
useradd -m -s /sbin/nologin -d /usr/lib/ckan -c "CKAN User" ckan
```

Then give `755` permission to the whole directory, so Apache can access it later on:

```bash
chmod 755 /usr/lib/ckan
```

Switch to ckan user and create virtualenv:

```bash
su -s /bin/bash - ckan
cd /usr/lib/ckan/
virtualenv --no-site-packages default
```

Then you can activate the virtualenv:

```bash
. /usr/lib/ckan/default/bin/activate
```

## 3. Installing CKAN


### 3.1 Install CKAN from source
First make sure you have the correct version of `setuptools`:

```bash
pip install setuptools==36.1
```

Then, install CKAN source:

```bash
pip install -e 'git+https://github.com/ckan/ckan.git@ckan-2.8.2#egg=ckan'
```

**Important Note**: We're using version `2.8.2`, so make sure you have the correct version in the Git url.

Install the required Python packages for CKAN:

```bash

pip install -r /usr/lib/ckan/default/src/ckan/requirements.txt
```

Deactivate and reactivate your virtualenv, to make sure you’re using the virtualenv’s copies of commands like paster rather than any system-wide installed copies:

```bash
deactivate
. /usr/lib/ckan/default/bin/activate
```

### 3.2 Setup PostgreSQL Database

First go back and login with the sudoer user.

Then, check that PostgreSQL is running properly:

```bash
sudo -u postgres psql -l
```

Check that the encoding of databases is UTF8, if not internationalization may be a problem. Since changing the encoding of PostgreSQL may mean deleting existing databases, it is suggested that this is fixed before continuing with the CKAN install.

Now, create the user for CKAN, and enter the user password when prompted for it:

```bash
sudo -u postgres createuser -S -D -R -P ckan_default
```

Finally, enable the PostGIS extension on the ckan_default database:

```bash
sudo -i -u postgres

```

Then install the extension via psql:

```bash
psql -d ckan_default
```

In psql console:

```sql
create extension postgis;

select PostGIS_version();
```
You should see output like this:
```
            postgis_version            
---------------------------------------
 2.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1
(1 row)

```

### 3.3 Create CKAN DataStore database

This creates the Data Store database and creates two types of access to it: read-only and read-write.

First create the user that has read-only access to the datastore:

```bash
sudo -u postgres createuser -S -D -R -P -l datastore_default
```

Then create the database, owned by `ckan_default`, as created in the previous step:

```bash
sudo -u postgres createdb -O ckan_default datastore_default -E utf-8
```



### 3.4 Install Solr

> Note that this is a bit different from the official CKAN installation gude. We install Solr manually to get the same version across different distributions instead relying on the provided version.
> Different distros provide varying versions of Solr, usually deployed differently on each. We want to make sure we have the same version everywhere.
> If you already have a Solr setup deployed (single instance or Solr Cloud), you can skip the installation part, and configure a Solr Core (or collection) with the provided Solr schema.


#### 3.4.1 Download and install Solr
Create a user for Solr, and a directory where we're going to install it:

```bash
sudo mkdir -p /opt/apps/solr
sudo useradd -m -d /opt/apps/solr -s /bin/bash solr
sudo chown -R solr /opt/apps/solr

```

Switch to user solr and to the installation location:
```bash
sudo -i -u solr
cd /opt/apps/solr
```

Download version 6.5.1 of Solr and unpack it:

```bash
wget https://archive.apache.org/dist/lucene/solr/6.5.1/solr-6.5.1.tgz
tar xzvf solr-6.5.1.tgz
mv solr-6.5.1 6.5.1  # Rename to the version so we get nice path `/opt/apps/solr/6.5.1`
rm solr-6.5.1.tgz  # Remove the downloaded archive
```

#### 3.4.2 Configure to run automatically

We're going to use `systemd` service to manage the state of Solr, thus integrating it as a system service.

First we need to create a Service file.

Create new file at `/etc/systemd/system/solr.service`

```
sudo touch /etc/systemd/system/solr.service
sudo chmod 664 /etc/systemd/system/solr.service
```

Add the following content of the file (run the editor in sudo mode - for example `sudo vim /etc/systemd/system/solr.service`):

```service
[Unit]
Description=Apache Solr
After=network.target

[Service]
Type=forking
ExecStart=/opt/apps/solr/6.5.1/bin/solr start
ExecReload=/opt/apps/solr/6.5.1/bin/solr restart
ExecStop=/opt/apps/solr/6.5.1/bin/solr stop
User=solr

[Install]
WantedBy=multi-user.target
```

Save and close.

Enable the systemd service - this will run Solr on startup:
```bash
sudo systemctl enable solr
```

Then run the service:

```bash
sudo systemctl start solr
```

To confirm it is running:

```bash
sudo systemctl status solr
● solr.service - Apache Solr
   Loaded: loaded (/etc/systemd/system/solr.service; disabled; vendor preset: disabled)
   Active: active (running) since нед 2020-08-09 14:21:48 CEST; 4s ago
  Process: 25527 ExecStart=/opt/apps/solr/6.5.1/bin/solr start (code=exited, status=0/SUCCESS)
 Main PID: 25601 (java)
   CGroup: /system.slice/solr.service
           └─25601 java -server -Xms512m -Xmx512m -XX:NewRatio=3 -XX:SurvivorRatio=4 -XX:TargetSurvivorRatio=90 -XX:MaxTenuringThreshold=8 -XX:+UseConcMark...

авг 09 14:21:42 centos-srv systemd[1]: Starting Apache Solr...
авг 09 14:21:48 centos-srv solr[25527]: [134B blob data]
авг 09 14:21:48 centos-srv solr[25527]: Started Solr server on port 8983 (pid=25601). Happy searching!
авг 09 14:21:48 centos-srv systemd[1]: Started Apache Solr.
```

### 3.4.3 Create CKAN core and configuration

To create CKAN Core, on a local installation, run:

```bash
sudo -u solr /opt/apps/solr/6.5.1/bin/solr create_core -c ckan
```

This will create a new Solr Core, with name ckan.

Then we must configure the core to use the specific CKAN configuration.

For this step, you'll need the config file from `ckanext-knowledgehub`. You can get these either from the [github master branch](https://raw.githubusercontent.com/keitaroinc/ckanext-knowledgehub/master/ckanext/knowledgehub/schema.xml), or from the local repository clone (see the steps for installing ckanext-knowledgehub).


```bash
sudo -i -u solr
cd /opt/apps/solr/6.5.1/server/solr/ckan/conf/
wget https://raw.githubusercontent.com/keitaroinc/ckanext-knowledgehub/master/ckanext/knowledgehub/schema.xml
```

Then edit the configuration file `solrconfig.xml`.

First set the Schema Factory to classic factory. This disables the automatic schema update, as we provide the schema ourselves.

Add the following to the main section:

```xml
  <!-- Classic Schema Factory-->
  <schemaFactory class="ClassicIndexSchemaFactory"/>
```

just above `<codecFactory class="solr.SchemaCodecFactory"/>`.

Then comment out the following processor configuration:
```xml
    <!--processor class="solr.AddSchemaFieldsUpdateProcessorFactory">
      <str name="defaultFieldType">strings</str>
      <lst name="typeMapping">
        <str name="valueClass">java.lang.Boolean</str>
        <str name="fieldType">booleans</str>
      </lst>
      <lst name="typeMapping">
        <str name="valueClass">java.util.Date</str>
        <str name="fieldType">tdates</str>
      </lst>
      <lst name="typeMapping">
        <str name="valueClass">java.lang.Long</str>
        <str name="valueClass">java.lang.Integer</str>
        <str name="fieldType">tlongs</str>
      </lst>
      <lst name="typeMapping">
        <str name="valueClass">java.lang.Number</str>
        <str name="fieldType">tdoubles</str>
      </lst>
    </processor-->
```

Alternatively, you can just copy the provided [solrconfig.xml](solrconfig.xml) file from the docs.

Save the changes, and restart Solr:

```bash
sudo systemctl restart solr
```


### 3.4 Create CKAN configuration files

Create the directory that will contain the configuration files (in `/etc`):

```bash
sudo mkdir -p /etc/ckan/default
sudo chown -R ckan /etc/ckan/

# This is for Ubuntu Only
sudo chown -R ckan /home/ckan/ckan/etc
```

Switch to `ckan` user, and activate the virtualenv:

```bash
sudo -i -u ckan
. /usr/lib/ckan/default/bin/activate
```

Create the storage directory for uploaded files (make sure CKAN has write privileges to this dir):

```bash
mkdir /home/ckan/data
```

**On CentOS:**
```
mkdir /usr/lib/ckan/data
```

Create the CKAN config file:

```bash
paster make-config ckan /etc/ckan/default/production.ini
```

Once the file is generated, we need to edit the file and set up these basic values:

* `sqlalchemy.url` must point to the CKAN database that was created in the previous step:
```
sqlalchemy.url = postgresql://ckan_default:pass@localhost/ckan_default?sslmode=disable
```

* `ckan.site_id=unhcr_knowledgehub` - Each site should have a unique ID.
* `ckan.site_url = http://knowledgehub.unhcr.org` - the real URL of the site, as it will be accessed later on. This is used to generate URLs inside CKAN.

DataStore DB urls:
* `ckan.datastore.write_url`  - This is the read-write access to the datastore database. Use the CKAN user here.
```
ckan.datastore.write_url = postgresql://ckan_default:pass@localhost/datastore_default
```
* `ckan.datastore.read_url` - Read-only access to the datastore database here (created in the previous step):
```
ckan.datastore.read_url = postgresql://datastore_default:pass@localhost/datastore_default
```

* `solr_url` - The url to the configured Solr with CKAN core.

```
solr_url = http://127.0.0.1:8983/solr/ckan
```


Link to `who.ini` file:

```bash
ln -s /usr/lib/ckan/default/src/ckan/who.ini /etc/ckan/default/who.ini
```

### 3.5 Create CKAN Database tables

This step is important to be performed immeditely after installing CKAN, before any additional extensions are installed.

This installs the core CKAN tables. If additional estensions are enabled at this point, there is a possibility that those plugins would require the base tables to be installed and may cause an error to be thrown.

To create the core tables, run (make sure the virtualenv is activated):

```bash
. /usr/lib/ckan/default/bin/activate
cd /usr/lib/ckan/default/src/ckan
paster db init -c /etc/ckan/default/production.ini
```

You should get:
```
Initialising DB: SUCCESS
```

**On CentOS 7** You will need to update the `pg_hba.conf` file to enable password authentication from localhost.

Edit file `/var/lib/pgsql/data/pg_hba.conf` to look like this:

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     peer
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
# IPv6 local connections:
host    all             all             ::1/128                 md5
# Allow replication connections from localhost, by a user with the
# replication privilege.
local   replication     postgres                                peer
host    replication     postgres        127.0.0.1/32            md5
host    replication     postgres        ::1/128                 md5
```

Then save and restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```


### 3.6 Create DataStore tables and permissions

CKAN provides paster command that generates the SQL for setting permissions on the datastore database.
You can pipe the SQL to `psql` connected to the database, by executing the following command:

```bash
paster --plugin=ckan datastore set-permissions -c /etc/ckan/default/production.ini | psql -h localhost -U ckan_default -d ckan_default 
```

### 3.7 Test the setup

Run CKAN in development mode with paster:

```
. /usr/lib/ckan/default/bin/activate
cd /usr/lib/ckan/default/src/ckan
paster serve /etc/ckan/default/production.ini
```

There should be no error in the output of this command.

Then open the CKAN url in browser (still running on port 5000): `http://<server-ip>:5000/`

You should see the CKAN welcome page.

> **CentOS7 Note** 
> 
> You may need to add the port to the firewall.
> ```bash
> sudo firewall-cmd --zone=public --add-port=5000/tcp --permanent
> sudo firewall-cmd --reload
> ```

### 3.8 Install Datapusher

1. Install required libraries

```bash
sudo apt install build-essential libxslt1-dev libxml2-dev git libffi-dev
```

**CentOS**

```
sudo yum install -y libxslt-devel libxml2-devel libffi-devel
```

2. switch to user ckan

```bash
sudo -i -u ckan  # Ubuntu

sudo su -s /bin/bash - ckan  # Centos
```

3. create a virtualenv for datapusher
```
virtualenv /usr/lib/ckan/datapusher
```

4. create a source directory and switch to it
```
mkdir /usr/lib/ckan/datapusher/src
cd /usr/lib/ckan/datapusher/src
```

5. clone the stable version of datapusher

```bash
git clone -b 0.0.16 https://github.com/ckan/datapusher.git
```

6. install the requirements and datapusher itself

```bash
. /usr/lib/ckan/datapusher/bin/activate
cd datapusher
pip install -r requirements.txt
python setup.py develop
```
7. Deploy datapusher to run with apache mod_wsgi

> This assumes that Apache has been set up. If not please read the section [Deployment - Installing Apache and nginx]() at the bottom of this document.


**Ubuntu Server**
First copy the site configuration for the datapusher:

```bash
sudo cp /usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher.conf /etc/apache2/sites-available/datapusher.conf
```

Edit the `datapusher.conf` file and add permissions for `/etc/ckan` directory. The full file should look like this:

```xml
<VirtualHost 0.0.0.0:8800>

    ServerName ckan

    # this is our app
    WSGIScriptAlias / /etc/ckan/datapusher.wsgi

    # pass authorization info on (needed for rest api)
    WSGIPassAuthorization On

    # Deploy as a daemon (avoids conflicts between CKAN instances)
    WSGIDaemonProcess datapusher display-name=demo processes=1 threads=15

    WSGIProcessGroup datapusher

    ErrorLog /var/log/apache2/datapusher.error.log
    CustomLog /var/log/apache2/datapusher.custom.log combined

    <Directory /etc/ckan>
    Options All
    AllowOverride All
    Require all granted
    </Directory>
</VirtualHost>

```


Copy the provided WSGI script:

```bash
sudo cp /usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher.wsgi /etc/ckan/
```

Copy the default setting script:

```bash
sudo cp /usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher_settings.py /etc/ckan/
```

Then add the port `8800` to the Apache ports file:

```bash
sudo vim /etc/apache2/ports.conf
```

and add:

```
Listen 8800
```

Enable the datapusher site, then reload:

```bash
sudo a2ensite datapusher
sudo systemctl restart apache2
```

Test the setup by calling:

```
curl http://localhost:8800
```

You should get:

```json
{"help":"\n        Get help at:\n        http://ckan-service-provider.readthedocs.org/."}
```

**CentOS**

First copy the site configuration for the datapusher:

```bash
sudo cp /usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher.conf /etc/httpd/conf.d/datapusher.conf
```

Edit the `datapusher.conf` file and add permissions for `/etc/ckan` directory. The full file should look like this:

```xml
<VirtualHost 0.0.0.0:8800>

    ServerName ckan

    # this is our app
    WSGIScriptAlias / /etc/ckan/datapusher.wsgi

    # pass authorization info on (needed for rest api)
    WSGIPassAuthorization On

    # Deploy as a daemon (avoids conflicts between CKAN instances)
    WSGIDaemonProcess datapusher display-name=demo processes=1 threads=15

    WSGIProcessGroup datapusher

    ErrorLog /var/log/httpd/datapusher.error.log
    CustomLog /var/log/httpd/datapusher.custom.log combined

    <Directory /etc/ckan>
    Options All
    AllowOverride All
    Require all granted
    </Directory>
</VirtualHost>

```


Copy the provided WSGI script:

```bash
sudo cp /usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher.wsgi /etc/ckan/
```

Copy the default setting script:

```bash
sudo cp /usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher_settings.py /etc/ckan/
```

Then add the port `8800` to the Apache config file (`/etc/httpd/conf/httpd.conf`):

```bash
sudo vim /etc/httpd/conf/httpd.conf
```

find the `Listen` directive and add another one (bellow the one for `8080`): 

```
Listen 8800
```

Change SELinux policy to allow the Apache to bind to port `8800`:

```bash
sudo semanage port -a -t http_port_t -p tcp 8800
```

Reload apache:

```bash
sudo systemctl restart httpd
```

Test the setup by calling:

```
curl http://localhost:8800
```

You should get:

```json
{"help":"\n        Get help at:\n        http://ckan-service-provider.readthedocs.org/."}
```


# Install Required CKAN Extensions

Knowledgehub depends on a couple of CKAN Extensions:
* [ckanext-validation](https://github.com/frictionlessdata/ckanext-validation)
* [ckanext-datarequests](https://github.com/keitaroinc/ckanext-datarequests)
* [ckanext-oauth2](https://github.com/keitaroinc/ckanext-oauth2)

## Install ckanext-validation

Switch to user `ckan`, activate the virtualenv then install the extension using `pip`:

```bash
sudo -i -u ckan
. /usr/lib/ckan/default/bin/activate
pip install --no-cache-dir -e "git+https://github.com/frictionlessdata/ckanext-validation.git#egg=ckanext-validation"

cd /usr/lib/ckan/default/
pip install -r src/ckanext-validation/requirements.txt

```

Validation extenstion requires database initialization. So after the installation run:

```bash
cd src/ckanext-validation/
paster validation init-db -c /etc/ckan/default/production.ini
```

### Add to CKAN plugins and test the installation

Edit the production configuration file (`/etc/ckan/default/production.ini`) and add the validation plugin:

```conf
ckan.plugins = recline_view validation stats
```

Save, then start CKAN with paster:

```bash
paster serve /etc/ckan/default/production.ini
```

## Install ckanext-datarequests

If not already switched, then switch to user `ckan` and activate the virtualenv:

```bash
sudo -i -u ckan
. /usr/lib/ckan/default/bin/activate
```

Install the extension using `pip`:

```bash
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-datarequests.git@kh_stable#egg=ckanext-datarequests"
```

Edit the production configuration file (`/etc/ckan/default/production.ini`) and add the validation plugin:

```conf
ckan.plugins = recline_view validation stats datarequests
```

Test the installation:

```bash
paster serve /etc/ckan/default/production.ini
```

> **Note**
>
> Due to a bug in `ckanext-datarequests`, you need to install `humanize` package manually at this step:
> ```bash
> pip install humanize==1.0.0
> ```

## Install ckanext-oauth2

If not already switched, then switch to user `ckan` and activate the virtualenv:

```bash
sudo -i -u ckan
. /usr/lib/ckan/default/bin/activate
```


Install the extension using `pip`:

```bash
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-oauth2.git@kh_stable#egg=ckanext-oauth2"
```

OAuth2 requires additional configuration to run properly. You need to have set up application and have generated keys and tokens for the OAuth2 protocol. Then those values have to be set up in the `production.ini` file.

Open `/etc/ckan/default/production.ini` and add these values (replace your real production keys and URLs):

```conf

# OAuth2 settings
ckan.oauth2.register_url = https://YOUR_OAUTH_SERVICE/users/sign_up
ckan.oauth2.reset_url = https://YOUR_OAUTH_SERVICE/users/password/new
ckan.oauth2.edit_url = https://YOUR_OAUTH_SERVICE/settings
ckan.oauth2.authorization_endpoint = https://YOUR_OAUTH_SERVICE/authorize
ckan.oauth2.token_endpoint = https://YOUR_OAUTH_SERVICE/token
ckan.oauth2.profile_api_url = https://YOUR_OAUTH_SERVICE/user
ckan.oauth2.client_id = YOUR_CLIENT_ID
ckan.oauth2.client_secret = YOUR_CLIENT_SECRET
ckan.oauth2.scope = profile other.scope
ckan.oauth2.rememberer_name = auth_tkt
ckan.oauth2.profile_api_user_field = JSON_FIELD_TO_FIND_THE_USER_IDENTIFIER
ckan.oauth2.profile_api_fullname_field = JSON_FIELD_TO_FIND_THE_USER_FULLNAME
ckan.oauth2.profile_api_mail_field = JSON_FIELD_TO_FIND_THE_USER_MAIL
ckan.oauth2.authorization_header = OAUTH2_HEADER

```

Refer to the OAuth2 setup document for exact values for these fields.


Add the `oauth2` plugin to the list of plugins:

```conf
ckan.plugins = recline_view validation stats datarequests oauth2
```

Test the istallation by running paster:

```bash
paster serve /etc/ckan/default/production.ini
```

## Activate the datastore extension

Edit the production config file (`/etc/ckan/default/production.ini`), and add `datastore` to the list of plugins (the order is important):

```conf
ckan.plugins = recline_view validation stats datastore datarequests oauth2
```

Remember to also check if the database URLs are set up properly as well:

```conf
ckan.datastore.write_url = postgresql://ckan_default:pass@localhost/datastore_default
ckan.datastore.read_url = postgresql://datastore_default:pass@localhost/datastore_default

```

Save, then test the installation running `paster`:

```bash
paster serve /etc/ckan/default/production.ini
```


## Activate the datapusher extension


Add `datapusher` to the list of active plugins in `/etc/ckan/default/production.ini`:

```conf
ckan.plugins = recline_view validation stats datastore datapusher datarequests oauth2
```

> Note the order of plugins must be as specified above.


In the same file, set the datapusher URL:

```conf
ckan.datapusher.url = http://127.0.0.1:8800/
```

Save the file, then restart Apache:

```bash
# Ubuntu
sudo systemctl restart apache2

# Centos
sudo systemctl restart httpd
```



# Install Knowledhub Extension

Switch to user `ckan` then activate the virtualenv:

```bash
# Ubuntu
sudo -i -u ckan
. /usr/lib/ckan/default/bin/activate

# Centos
sudo su -s /bin/bash - ckan
. /usr/lib/ckan/default/bin/activate
```

Install the extension and required Python packages with `pip`:

```bash
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-knowledgehub.git#egg=ckanext-knowledgehub"

# Due to some of the packages requiring newer version of setuptools, we need to uninstall, then reinstall setuptools
pip uninstall setuptools
pip install setuptools

pip install --no-cache-dir -r "/usr/lib/ckan/default/src/ckanext-knowledgehub/requirements.txt" 
```

>Due to mismatch of PostgreSQL driver (psycopg2) version used in CKAN and HDX API library, we must reinstall the correct version:
>```bash
>pip uninstall psycopg2-binary -y
>pip uninstall psycopg2 -y
>pip install --no-cache-dir psycopg2==2.7.3.2
>``` 

Download language model for Spacy:

```bash
python -m spacy download en_core_web_sm
```



# Configure Production Deployment

## Install Apache and nginx

1. Install Apache, nginx and related libraries

**Ubuntu Server**:

```bash
sudo apt-get install -y nginx apache2 libapache2-mod-wsgi libapache2-mod-rpaf libpq5
```

**CentOS 7**:

```bash
sudo yum install -y nginx httpd mod_wsgi 
```

> Note that `mod_rpaf` is not available in the stadard CentOS repositories. We'll skip for this installation.



2. Create wsgi file `/etc/ckan/default/apache.wsgi`:

```
import os
activate_this = os.path.join('/usr/lib/ckan/default/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

from paste.deploy import loadapp
config_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'production.ini')
from paste.script.util.logging_config import fileConfig
fileConfig(config_filepath)
application = loadapp('config:%s' % config_filepath)
```

Make the user `ckan` owner of the file:

```bash
sudo chown ckan /etc/ckan/default/apache.wsgi
```

3. Create the Apache config file at `/etc/apache2/sites-available/ckan_default.conf`:

```apache
<VirtualHost 127.0.0.1:8080>
    ServerName knowledhehub.ubuntu.unhcr.org
    ServerAlias www.knowledhehub.ubuntu.unhcr.org
    WSGIScriptAlias / /etc/ckan/default/apache.wsgi

    # Pass authorization info on (needed for rest api).
    WSGIPassAuthorization On

    # Deploy as a daemon (avoids conflicts between CKAN instances).
    WSGIDaemonProcess ckan_default display-name=ckan_default processes=2 threads=15

    WSGIProcessGroup ckan_default

    ErrorLog /var/log/apache2/ckan_default.error.log
    CustomLog /var/log/apache2/ckan_default.custom.log combined

    <IfModule mod_rpaf.c>
        RPAFenable On
        RPAFsethostname On
        RPAFproxy_ips 127.0.0.1
    </IfModule>

    <Directory />
        Require all granted
    </Directory>

</VirtualHost>
```

Replace `knowledhehub.ubuntu.unhcr.com` with the actual doman name of the site.

**CentOS 7**:

Centos locations are different from Ubuntu. We're going to create new VirtualHost definition in `/etc/httpd/conf.d/knowledhehub.centos.unhcr.org.conf`.


First, remove the welcome page from the apache server:

```
sudo mv /etc/httpd/conf.d/welcome.conf /etc/httpd/conf.d/welcome.conf_backup
```

Then create the file: `/etc/httpd/conf.d/knowledhehub.centos.unhcr.org.conf` with the following content:


```
<VirtualHost 127.0.0.1:8080>
    ServerName knowledhehub.centos.unhcr.org
    ServerAlias www.knowledhehub.centos.unhcr.org
    WSGIScriptAlias / /etc/ckan/default/apache.wsgi

    # Pass authorization info on (needed for rest api).
    WSGIPassAuthorization On

    # Deploy as a daemon (avoids conflicts between CKAN instances).
    WSGIDaemonProcess ckan_default display-name=ckan_default processes=2 threads=15

    WSGIProcessGroup ckan_default

    ErrorLog /var/log/httpd/ckan_default.error.log
    CustomLog /var/log/httpd/ckan_default.custom.log combined

    <IfModule mod_rpaf.c>
        RPAFenable On
        RPAFsethostname On
        RPAFproxy_ips 127.0.0.1
    </IfModule>

    <Directory />
        Require all granted
    </Directory>

</VirtualHost>
```

> Remember to replace `knowledhehub.centos.unhcr.org` with the correct domain name both in the config file and as the file name.


Site is enabled by default.

Reload the service:

```
sudo systemctl restart httpd
```

**Open http port through firewall**

Run the following command:
```
sudo firewall-cmd --permanent --add-service=http
```



4. Modify the Apache ports file `/etc/apache2/ports.conf`. We want the apache to listen to port 8080 instead of port 80.

> On **CentOS** edit file `/etc/httpd/conf/httpd.conf`

Change
```
Listen 80
```

To

```
Listen 8080
```

5. Create `nginx` configuration file at `/etc/nginx/sites-available/ckan`:

```
proxy_cache_path /tmp/nginx_cache levels=1:2 keys_zone=cache:30m max_size=250m;
proxy_temp_path /tmp/nginx_proxy 1 2;

server {
    client_max_body_size 100M;
    location / {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Host $host;
        proxy_cache cache;
        proxy_cache_bypass $cookie_auth_tkt;
        proxy_no_cache $cookie_auth_tkt;
        proxy_cache_valid 30m;
        proxy_cache_key $host$scheme$proxy_host$request_uri;
        # In emergency comment out line to force caching
        # proxy_ignore_headers X-Accel-Expires Expires Cache-Control;
    }

}
```

**CentOS**

We must create the config directories `sites-available` and `sites-enabled`:

```bash
sudo mkdir /etc/nginx/sites-available /etc/nginx/sites-enabled
```

Edit `/etc/nginx/nginx.conf`, and add the following inside the `http` block:

```
include /etc/nginx/sites-enabled/*.conf
server_names_hash_bucket_size 64;
```

or use the following configuration if only using it for CKAN deployment:

```
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

# Load dynamic modules. See /usr/share/doc/nginx/README.dynamic.
include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

http {
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    # Load modular configuration files from the /etc/nginx/conf.d directory.
    # See http://nginx.org/en/docs/ngx_core_module.html#include
    # for more information.
    include /etc/nginx/conf.d/*.conf;

    # Load enabled sites.
    include /etc/nginx/sites-enabled/*;
    server_names_hash_bucket_size 64;

}

```


Add the above configuration at `/etc/nginx/sites-available/ckan.conf`.

Enable the site:

```
sudo ln -s /etc/nginx/sites-available/ckan.conf /etc/nginx/sites-enabled/ckan.conf
```

Restart nginx:

```
sudo systemctl restart nginx
```

> If SE Linux, you must allow nginx to connect to upstream server. Execute:
>```
>sudo setsebool httpd_can_network_connect on -P
>```

6. Enable CKAN site with Apache and nginx


**Ubuntu Server**
```bash
sudo a2ensite ckan_default
sudo a2dissite 000-default
sudo rm -vi /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/ckan /etc/nginx/sites-enabled/ckan_default
sudo service apache2 reload
sudo service nginx reload
```

**CentOS**

```bash
sudo systemctl restart httpd
sudo systemctl restart nginx
```

