#!/bin/bash

set -e

source ../.env

response="{ \"apikey\": \"${HUB_API_KEY}\", \"task\": \"firmware\", \"answer\": { \"confirmation\": \"${1}\" } }"

echo "${response}"

curl -X POST -H "Content-Type: application/json" -d "${response}" "${HUB_URL}/verify"
