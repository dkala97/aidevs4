#!/bin/bash

set -e

source ../.env

response="{ \"apikey\": \"${HUB_API_KEY}\", \"task\": \"negotiations\", \"answer\": { \"action\": \"check\" } }"

curl -X POST -H "Content-Type: application/json" -d "${response}" "${HUB_URL}/verify"
