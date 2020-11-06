[![Build Status](https://travis-ci.com/keitaroinc/ckanext-knowledgehub.svg?branch=master)](https://travis-ci.com/keitaroinc/ckanext-knowledgehub)
[![Coverage Status](https://coveralls.io/repos/github/keitaroinc/ckanext-knowledgehub/badge.svg?branch=master)](https://coveralls.io/github/keitaroinc/ckanext-knowledgehub?branch=master)

# ckanext-knowledgehub

This is the main repo for the Knowledge Hub on Displaced Populations in the MENA Region. All of the CKAN customizations are added in this extension.

# Table of contents
  - [Getting started](#getting-started)
     - [Requirements](#requirements)
     - [Additional Requirements](#additional-requirements)
     - [Installation](#installation)
     - [Config Settings](#config-settings)
 - [Development](#development)
     - [Development Installation](#development-installation)
     - [Modify CSS](#modify-css)
     - [Running the Tests](#running-the-tests)
 - [Install spaCy](#install-spacy)
 - [User Intents](#user-intents)
 - [Production Deployment](#full-portal-production-deployment)


# Getting started

### Requirements

This extension requires CKAN 2.8.x version.


### Additional Requirements

* [Data Requests](https://github.com/conwetlab/ckanext-datarequests)
* [Validation](https://github.com/frictionlessdata/ckanext-validation)
* [OAuth2 (login with Azure accounts)](https://github.com/keitaroinc/ckanext-oauth2)

### Installation

To install ckanext-knowledgehub:

1. Activate your CKAN virtual environment, for example:

```
. /usr/lib/ckan/default/bin/activate
```

2. Install the ckanext-knowdledgehub Python package into your virtual environment:

```
pip install ckanext-knowledgehub
```
3. Initialize the tables:
```
knowledgehub -c /etc/ckan/default/production.ini db init
```
4. Add ``knowledgehub`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

5. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

```
sudo service apache2 reload
```

### Config Settings

These are the required configuration options used by the extension:

1. The number of themes shown per page
```
# (optional, default: 10).
ckanext.knowledgehub.themes_per_page = 20
```
2. The number of sub-themes shown per page
 ```
# (optional, default: 10).
ckanext.knowledgehub.sub_themes_per_page = 20
```
3. The number of dashboards shown per page
```
# (optional, default: 10).
ckanext.knowledgehub.dashboards_per_page = 20
```
4. Predictive Search
     - Length of the sequence after which the model can start predict, recommended at least 10 chars long
     ```
     # (optional, default: 10)
     ckanext.knowledgehub.rnn.sequence_length = 12
     ```
     - Number of chars to be skipped in generation of next sentence
     ```
     # (optional, default: 1)
     ckanext.knowledgehub.rnn.sentence_step = 2
     ```
     - Number of predictions to return
     ```
     # (optional, default: 3)
     ckanext.knowledgehub.rnn.number_predictions = 2
     ```
     - Minimum length of the corpus after it should start to predict
     ```
     # (optional, default: 10000)
     ckanext.knowledgehub.rnn.min_length_corpus = 300
     ```
     - Maximum epochs to learn
     ```
     # (optional, default: 50)
     ckanext.knowledgehub.rnn.max_epochs = 30
     ```
     - Full path to the RNN weights model
     ```
     # (optional, default: ./keras_model_weights.h5)
     ckanext.knowledgehub.rnn.model_weights = /home/user/model_weights.h5
     ```
     - Full path to the RNN network model
     ```
     # (optional, default: ./keras_model_network.h5)
     ckanext.knowledgehub.rnn.model_network = /home/user/model_network.h5
     ```
     - Full path to the model history
     ```
     # (optional, default: ./history.p)
     ckanext.knowledgehub.rnn.history = /home/user/history.p
     ```
5. Limit search facets
    - Display only functional units, joint analysis and tags as facets(filters) on home page search
    ```
    # ( mandatory )
    search.facets = organization groups tags
    ```

    - Which facets(filters) to show for research-questions, visualizations and dashboards
    ```
    # (optional, default: 'organizations groups tags)
    knowledgehub.search.facets = organizations groups tags
    ```
6. HDX Configuration
    ```
    # ( mandatory )
    ckanext.knowledgehub.hdx.api_key = <API_KEY>
    ```
    ```
    # ( mandatory )
    ckanext.knowledgehub.hdx.site = <HDX_SITE:test or prod>
    ```
    ```
    # ( mandatory )
    ckanext.knowledgehub.hdx.owner_org = <HDX_OWNER_ORGANIZATION_ID>
    ```
    ```
    # ( mandatory )
    ckanext.knowledgehub.hdx.dataset_source = knowledgehub
    ```
    ```
    # ( mandatory )
    ckanext.knowledgehub.hdx.maintainer = <HDX_MAINTAINER>
    ```
   
7. Advanced solr search parameters
    - Set the mm (minimum should match) DisMax query parameter
    ```
    # ( optional, default: 1<30% )
    ckanext.knowledgehub.search.mm = 1
    ```

# Development

### Development installation

To install ckanext-knowledgehub for development, activate your CKAN virtualenv
and do:

```
git clone https://github.com/keitaroinc/ckanext-knowledgehub.git
cd ckanext-knowledgehub
python setup.py develop
pip install -r dev-requirements.txt
```

To initialize the tables do:
```
knowledgehub -c /etc/ckan/default/production.ini db init
```

All code MUST follow [PEP8 Style Guide](https://www.python.org/dev/peps/pep-0008/). Most editors have plugins or integrations and automatic checking for PEP8 compliance so make sure you use them.

You should add a pre-commit hook that will
check for PEP8 errors. Follow the next steps to enable this check.

1. Make sure you have installed the PEP8 style checker:
```
$ pip install pycodestyle
```
2. In the `.git/hooks` folder which is located inside the project's root
directory, create a file named `pre-commit` and inside put [this code](https://github.com/keitaroinc/pep8-git-hook/blob/master/pre-commit).
3. Make `pre-commit` executable by running this command:
```
$ chmod +x ckanext-knowledgehub/.git/hooks/pre-commit
```
Now, every time you commit code, the pre-commit hook will run and check for
PEP8 errors.

### Modify CSS

This extension uses LESS for styles. All changes must be made in one of the LESS
files located in the `ckanext-knowledgehub/ckanext/knowledgehub/fanstatic/less` folder.

Gulp.js is used for building CSS assets.

In order to build all CSS assets **run `node_modules/gulp/bin/gulp.js` once**. Gulp.js is watching for changes in the source LESS assets and will rebuild CSS on each change. If you have gulp.js installed globally on the system, you can just type `gulp` to run it.

### Running the Tests

To run the tests, first make sure that you have installed the required
development dependencies in CKAN, which can be done by running the following
command in the CKAN's `src` directory:

```
pip install -r dev-requirements.txt
```

After that just type this command to actually run the tests in the extension.

```
nosetests --ckan --with-pylons=test.ini
```
To run the tests and produce a coverage report, first make sure you have coverage installed in your virtualenv (pip install coverage) then run:

```
nosetests \
    -v \
    -s \
    --ckan \
    --with-coverage \
    --with-pylons=test.ini  \
    --cover-package=ckanext.knowledgehub \
    --cover-inclusive \
    --cover-erase \
    --cover-tests \
    --cover-html \
    ckanext/knowledgehub/tests
```

# Search Index Rebuilding

The installed extension offers rebuilding of the Solr index for multiple types of indexed documents.

To rebuild the full index (CKAN core search index and the other document types such as dashboards, visualizations and research questions), run the following command:

```bash
knowledgehub -c /etc/ckan/default/production.ini search-index rebuild
```

If you need to rebuild the index for specific document type (model), then you specify the `--model` parameter:

```bash
knowledgehub -c /etc/ckan/default/production.ini search-index rebuild --model dashboard
```

This would rebuild the index for dashboards.

Avalilable model types are:
* `ckan` - rebuilds the CKAN core (package) index,
* `dashboard` - rebuilds the dasboards index,
* `research-question` - rebuilds the research questions index and
* `visualization` - rebuilds the visualizations index.

If you specify `--model=all`, all indexes will be rebuilt (same as not specifying `--model` at all).

# Install Spacy

```bash
pip install -U setuptools # optional, only if there is an error about PEP 517 "BackendUnavailable"
pip install -U spacy
python -m spacy download en_core_web_sm
```

# User Intents

User intents are extracted from the user queries in a batch process that is run
periodically.

The following command updates the latest user intents and should be run at least
once a day:

```bash
knowledgehub -c /etc/ckan/default/production.ini intents update
```

The crontab should look something like this:

```cron
0 0 * * * knowledgehub -c /etc/ckan/default/production.ini intents update >/dev/null 2>&1
```

# Data Quality

Data Quality is measured across the six primary dimensions for data quality assessment.

A lot more details are available in the dedicated [documentation section](docs/data-qualtiy-metrics.md).

# Predictive search

The preditive search functinality predict the next n characters in the word or the next most possible word.
The training data is consist of title and description of all entities on Knowledge hub including themes, sub-themes,
research questions, datasets, visualizations and dashboards. Before it starts predict the machine learning model has to be trained.
By default user should write 10 characters in the search box on home page before it starts to predict.

Run the command for predictive search periodically( daily or weekly is recommended ).
This command will start training the model:

```
knowledgehub  -c /etc/ckan/default/production.ini predictive_search train
```

There is a action that can run CLI commands for Knowledge Hub.
This example shows how to run the above command through the API action:
```
curl -v 'http://hostname/api/3/action/run_command' -H'Authorization: API-KEY' -d '{"command": "predictive_search train"}'
```


# Oauth2 extension installation steps 

Install the extension, following the instructions provided: https://github.com/conwetlab/ckanext-oauth2

In the .ini file, add the following settings:
```
ckan.oauth2.jwt.enable = true
ckan.oauth2.authorization_endpoint = <YOUR_AUTH_ENDPOINT>
ckan.oauth2.token_endpoint = <YOUR_TOKEN_ENDPOINT>
ckan.oauth2.profile_api_url = https://graph.microsoft.com/v1.0/me
ckan.oauth2.client_id = <YOUR_CLIENT_ID>
ckan.oauth2.client_secret = <YOUR_CLIENT_SECRET>
ckan.oauth2.scope = profile openid email
ckan.oauth2.profile_api_user_field = unique_name
ckan.oauth2.profile_api_fullname_field = name
ckan.oauth2.profile_api_mail_field = unique_name
ckan.oauth2.authorization_header = Authorization
```

Note: The authorization endpoint, as well as the token endpoint, can be found in the Azure AD. After you navigate to your application, in the Overview tab, there will be a button called Endpoints. After you click it, a new tab will be opened with the information you need. Alternatively, the data can be found in the OpenID Connect metadata document. 
Below this Overview tab, there will be one called Certificates and Secrets, where you can create a secret and add it in the .ini file.


# Full Portal Production Deployment

For setting up full CKAN instance of Knowledgehub portal for production use,
please refer to the [Installation Guide](docs/installation-guide.md).

The guide contains instruction on how to install and deploy the portal for production use on Ubuntu Server 18.04 or CentOS 7.
