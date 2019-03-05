#!/bin/bash

echo "[extra_scripts.sh] Starting ckan workers"
paster --plugin=ckan jobs worker bulk --config="${APP_DIR}/production.ini" > /tmp/worker-bulk.log 2>&1 &
paster --plugin=ckan jobs worker priority --config="${APP_DIR}/production.ini" > /tmp/worker-priority.log 2>&1 &
paster --plugin=ckan jobs worker --config="${APP_DIR}/production.ini" > /tmp/worker.log 2>&1 &
echo "[extra_scripts.sh] Ckan workers started"

