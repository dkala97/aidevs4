#!/bin/bash

set -e

source ../.env

rm data/* || true
mkdir -p data || true

pushd data

wget ${HUB_URL}/data/${HUB_API_KEY}/failure.log

popd
