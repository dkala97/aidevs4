#!/bin/bash

set -e

source ../.env

query="{ \"apikey\": \"${HUB_API_KEY}\", \"task\": \"reactor\", \"answer\": { \"command\": \"reset\" } }"

curl -f -X POST -H "Content-Type: application/json" -d "${query}" "${HUB_URL}/verify"
