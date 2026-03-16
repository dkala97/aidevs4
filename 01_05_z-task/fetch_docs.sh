#!/bin/bash

set -e

source ../.env

rm data/docs/* || true
mkdir -p data/docs

pushd data/docs

query="{ \"apikey\": \"${HUB_API_KEY}\", \"task\": \"railway\", \"answer\": { \"action\": \"help\" } }"

curl -f -X POST -H "Content-Type: application/json" -d "${query}" "${HUB_URL}/verify"  -o API.md

popd
