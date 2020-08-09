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
sudo yum install -y python-devel postgresql-server postgresql-contrib python-pip python-virtualenv postgresql-devel git redis postgis wget lsof
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
> sudo firewall-cmd --zone=public --add-port=5000 --permanent
> sudo firewall-cmd --reload
> ```

### 3.8 Install Datapusher

<TODO>

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

cd ckan/lib/default/
pip install -r src/ckanext-validation/requirements.txt

```

Validation extenstion requires database initialization. So after the installation run:

```bash
cd src/ckanext-validation/
paster validation init-db -c /etc/ckan/default/production.ini
```

### Add to CKAN plugins and test the installation

Edit the production configuration file (`/etc/ckan/default/production.ini`) and add the validation plugin:

```config
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

```config
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

```config

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

```config
ckan.plugins = recline_view validation stats datarequests oauth2
```

Test the istallation by running paster:

```bash
paster serve /etc/ckan/default/production.ini
```

## Activate the datastore extension

Edit the production config file (`/etc/ckan/default/production.ini`), and add `datastore` to the list of plugins (the order is important):

```config
ckan.plugins = recline_view validation stats datastore datarequests oauth2
```

Remember to also check if the database URLs are set up properly as well:

```config
ckan.datastore.write_url = postgresql://ckan_default:pass@localhost/datastore_default
ckan.datastore.read_url = postgresql://datastore_default:pass@localhost/datastore_default

```

Save, then test the installation running `paster`:

```bash
paster serve /etc/ckan/default/production.ini
```


## Activate the datapusher extension

<todo>

# Install Knowledhub Extension

# Configure Production Deployment

