#!/bin/bash

set -e

source ../.env

rm data/docs/* || true
mkdir -p data/docs

pushd data/docs

wget ${HUB_URL}/dane/drone.html
wget ${HUB_URL}/data/${HUB_API_KEY}/drone.png

popd
