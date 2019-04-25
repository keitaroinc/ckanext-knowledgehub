.. You should enable this project on travis-ci.org and coveralls.io to make
   these badges work. The necessary Travis and Coverage config files have been
   generated for you.

.. image:: https://travis-ci.com/keitaroinc/ckanext-knowledgehub.svg?branch=master
    :target: https://travis-ci.com/keitaroinc/ckanext-knowledgehub

=============
ckanext-knowledgehub
=============

.. Put a description of your extension here:
   What does it do? What features does it have?
   Consider including some screenshots or embedding a video!


------------
Requirements
------------

For example, you might want to mention here which versions of CKAN this
extension works with.


------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-knowledgehub:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-knowledgehub Python package into your virtual environment::

     pip install ckanext-knowledgehub

3. Initialize the tables::

     knowledgehub -c /etc/ckan/default/production.ini db init

4. Add ``knowledgehub`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

5. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config Settings
---------------

These are required configuration settings used by the extension::

    # Some required configuration setting
    ckan.example_setting = ...

These are the optional configuration settings used by the extension::

    # The number of themes shown per page
    # (optional, default: 10).
    ckanext.knowledgehub.themes_per_page = 20

    # The number of sub-themes shown per page
    # (optional, default: 10).
    ckanext.knowledgehub.sub_themes_per_page = 20

    # The number of dashboards shown per page
    # (optional, default: 10).
    ckanext.knowledgehub.dashboards_per_page = 20

------------------------
Development Installation
------------------------

To install ckanext-knowledgehub for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/duskobogdanovski/ckanext-knowledgehub.git
    cd ckanext-knowledgehub
    python setup.py develop
    pip install -r dev-requirements.txt

To initialize the tables do::

    knowledgehub -c /etc/ckan/default/production.ini db init


-----------------
Running the Tests
-----------------

To run the tests, do::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.knowledgehub --cover-inclusive --cover-erase --cover-tests


---------------------------------
Registering ckanext-knowledgehub on PyPI
---------------------------------

ckanext-knowledgehub should be availabe on PyPI as
https://pypi.python.org/pypi/ckanext-knowledgehub. If that link doesn't work, then
you can register the project on PyPI for the first time by following these
steps:

1. Create a source distribution of the project::

     python setup.py sdist

2. Register the project::

     python setup.py register

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the first release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do::

       git tag 0.0.1
       git push --tags


----------------------------------------
Releasing a New Version of ckanext-knowledgehub
----------------------------------------

ckanext-knowledgehub is availabe on PyPI as https://pypi.python.org/pypi/ckanext-knowledgehub.
To publish a new version to PyPI follow these steps:

1. Update the version number in the ``setup.py`` file.
   See `PEP 440 <http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers>`_
   for how to choose version numbers.

2. Create a source distribution of the new version::

     python setup.py sdist

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.2 then do::

       git tag 0.0.2
       git push --tags
