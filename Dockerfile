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
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-validation/requirements.txt"

# Set plugins
ENV CKAN__PLUGINS envvars \
                  validation \
                  knowledgehub \
                  stats \
                  text_view \
                  image_view \
                  recline_view \
                  datastore \
                  datapusher

RUN mkdir -p /var/lib/ckan/default && chown -R ckan:ckan /var/lib/ckan/default
VOLUME /var/lib/ckan/default

# Load envvars plugin on ini file
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.plugins = ${CKAN__PLUGINS}"

COPY prerun.py /srv/app/prerun.py
COPY extra_scripts.sh /srv/app/extra_scripts.sh

CMD ["/srv/app/start_ckan.sh"]
