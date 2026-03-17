#!/bin/bash

set -e

source ../.env

./app.py --query_file query.md
