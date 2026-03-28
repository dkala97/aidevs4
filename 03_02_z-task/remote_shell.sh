#!/bin/bash

set -e

source ../.env

query="{ \"apikey\": \"${HUB_API_KEY}\", \"cmd\": \"$1\" }"

curl -f -X POST -H "Content-Type: application/json" -d "${query}" "${HUB_URL}/api/shell"
