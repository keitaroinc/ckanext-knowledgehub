
# ckanext-knowledgehub

[![Build Status](https://travis-ci.com/keitaroinc/ckanext-knowledgehub.svg?branch=master)](https://travis-ci.com/keitaroinc/ckanext-knowledgehub)

A CKAN extension to create CKAN Customization for Knowledge Hub on Displaced Populations in the MENA Region.

- [Installation](#installation)
- [Config Settings](#config-settings)
- [Development Installation](#development-installation)
- [Modify CSS](#modify-css)
- [Running the Tests](#running-the-tests)


### Requirements

This extension is being developed against CKAN 2.8.x version.





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

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

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

### Development Installation

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
nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.knowledgehub --cover-inclusive --cover-erase --cover-tests
```
