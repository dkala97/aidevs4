#!/bin/bash

set -e

source ../.env

rm dane/regulamin/* || true
mkdir -p dane/regulamin || true

pushd dane/regulamin

data_url_base="${HUB_URL}/dane/doc"

wget "${data_url_base}/index.md"

for included_file in `grep "include file=" index.md | grep -o '"[^"]*"' | tr -d '"'`; do
    wget "${data_url_base}/${included_file}"
done


popd
