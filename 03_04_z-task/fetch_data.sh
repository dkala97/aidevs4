#!/bin/bash

set -e

source ../.env

rm data/* || true
mkdir -p data || true

pushd data

wget ${HUB_URL}/dane/s03e04_csv/cities.csv
wget ${HUB_URL}/dane/s03e04_csv/connections.csv
wget ${HUB_URL}/dane/s03e04_csv/items.csv

popd
