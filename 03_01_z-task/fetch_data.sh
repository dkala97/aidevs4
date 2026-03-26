#!/bin/bash

set -e

source ../.env

rm -r workspace/* || true
mkdir -p workspace/data/zip
mkdir -p workspace/data/raw

pushd workspace/data/raw

wget ${HUB_URL}/dane/sensors.zip
unzip sensors.zip
mv sensors.zip ../zip/

popd
