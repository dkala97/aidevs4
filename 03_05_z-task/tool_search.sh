#!/bin/bash

set -e

source ../.env

response="{ \"apikey\": \"${HUB_API_KEY}\", \"query\": \"$1\" }"

curl -X POST -H "Content-Type: application/json" -d "${response}" "${HUB_URL}/api/toolsearch"
