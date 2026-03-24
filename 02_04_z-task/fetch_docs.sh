#!/bin/bash

set -e

source ../.env

rm data/docs/* || true
mkdir -p data/docs

pushd data/docs

query="{ \"apikey\": \"${HUB_API_KEY}\", \"action\": \"help\", \"page\": 1 }"

curl -f -X POST -H "Content-Type: application/json" -d "${query}" "${HUB_URL}/api/zmail"  -o API.md

popd
