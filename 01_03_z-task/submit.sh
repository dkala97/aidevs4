#!/bin/bash

source ../.env

endpoint_url=${AZYL_MY_HTTP_URL}
session_id="e3076977-5ee5-4c42-867c-e110fa43863c"

curl -X POST \
    -H "Content-Type: application/json" \
    -d "{ \"apikey\": \"${HUB_API_KEY}\", \"task\": \"proxy\", \"answer\": { \"url\": \"${endpoint_url}\", \"sessionID\": \"${session_id}\" } }" \
    "${HUB_URL}/verify"
