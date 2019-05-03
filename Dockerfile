FROM keitaro/ckan:2.8.2-clean

MAINTAINER Keitaro <info@keitaro.com>

USER root

RUN apk add --update-cache \
    --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ \
    --allow-untrusted \
    geos \
    geos-dev
RUN apk add \
    bash \
    g++ \
    gcc \
    libffi-dev \
    libstdc++ \
    libxml2 \
    libxml2-dev \
    libxslt \
    libxslt-dev \
    make \
    musl-dev \
    pcre \
    python2-dev \
    openssl-dev \
    py-lxml \
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
    # googleanalytics
    pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-googleanalytics.git#egg=ckanext-googleanalytics" && \
    pip install -r ckanext-googleanalytics/requirements.txt

# Set plugins
ENV CKAN__PLUGINS envvars \
                  recline_view \
                  validation \
                  knowledgehub \
                  disqus \
                  stats \
                  datastore \
                  datapusher \
                  datarequests \
                  googleanalytics

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

CMD ["/srv/app/start_ckan.sh"]
