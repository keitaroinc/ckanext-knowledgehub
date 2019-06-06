FROM keitaro/ckan:2.8.2-bionic

MAINTAINER Keitaro <info@keitaro.com>

USER root

RUN apt-get update && apt-get install -y \
    libgeos-dev \
    g++ \
    gcc \
    libffi-dev \
    libxml2-dev \
    libxslt1.1 \
    libxslt1-dev \
    make \
    musl-dev \
    libpcre3 \
    python-dev \
    unixodbc-dev \
    freetds-dev

# Install Cython needed for pymssql
RUN pip install cython && \
    # Install extensions
    # knowledgehub
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-knowledgehub.git#egg=ckanext-knowledgehub" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-knowledgehub/requirements.txt" && \
    # validation
    pip install --no-cache-dir -e "git+https://github.com/frictionlessdata/ckanext-validation.git#egg=ckanext-validation" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-validation/requirements.txt" && \
    # datarequests
    pip install --no-cache-dir -e "git+https://github.com/conwetlab/ckanext-datarequests.git#egg=ckanext-datarequests" && \
    # disqus
    pip install --no-cache-dir -e "git+https://github.com/okfn/ckanext-disqus#egg=ckanext-disqus"

# Set plugins
ENV CKAN__PLUGINS envvars \
                  recline_view \
                  validation \
                  knowledgehub \
                  disqus \
                  stats \
                  datastore \
                  datapusher \
                  datarequests

RUN mkdir -p /var/lib/ckan/default && chown -R ckan:ckan /var/lib/ckan/default
VOLUME /var/lib/ckan/default

# Load envvars plugin on ini file
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.plugins = ${CKAN__PLUGINS}"
# Remove recline view
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.views.default_views = recline_view"
# Set extra resource fields that should be indexed by SOLR
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.extra_resource_fields = theme sub_theme research_question"
# Show data request badge
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.datarequests.show_datarequests_badge = true"
# Set up Disqus
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "disqus.name = knowledgehub-ckan"
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "disqus.disqus_url = knowledgehub-staging.keitaro.app"

COPY prerun.py /srv/app/prerun.py
COPY extra_scripts.sh /srv/app/docker-entrypoint.d/extra_scripts.sh

RUN chown -R ckan:ckan /srv/app/src/ckan/

CMD ["/srv/app/start_ckan.sh"]