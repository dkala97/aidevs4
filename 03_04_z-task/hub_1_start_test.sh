#!/bin/bash

set -e

source ../.env

tools_schema=$(cat tools.json)
tools_schema=$(echo "$tools_schema" | sed "s|TOOL_API_URL|${AZYL_MY_HTTP_URL}|g")

response="{ \"apikey\": \"${HUB_API_KEY}\", \"task\": \"negotiations\", \"answer\": { \"tools\": ${tools_schema} } }"

curl -X POST -H "Content-Type: application/json" -d "${response}" "${HUB_URL}/verify"
