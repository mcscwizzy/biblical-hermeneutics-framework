#!/bin/sh
set -eu

archive_path=${1:?archive path is required}
output_path=${2:?output database path is required}
source_url=${3:?source URL is required}
source_sha256=${4:?source SHA-256 is required}

archive_dir=$(dirname "$archive_path")
mkdir -p "$archive_dir"

curl --fail --silent --show-error --location --retry 3 --retry-delay 1 \
  "$source_url" \
  --output "$archive_path"

printf '%s  %s\n' "$source_sha256" "$archive_path" | sha256sum --check --status

python -m framework.commentary import-tyndale \
  --source "$archive_path" \
  --output "$output_path" \
  --source-url "$source_url" \
  --strict

python -m framework.commentary check-tyndale --database "$output_path"
