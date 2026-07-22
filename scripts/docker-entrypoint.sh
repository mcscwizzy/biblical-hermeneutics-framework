#!/bin/sh
set -eu

if [ -n "${BHF_LEXICAL_DATABASE_PATH:-}" ] \
  && [ ! -f "$BHF_LEXICAL_DATABASE_PATH" ] \
  && [ -f /app/.bhf-seed/lexicon.sqlite ]; then
  mkdir -p "$(dirname "$BHF_LEXICAL_DATABASE_PATH")"
  cp /app/.bhf-seed/lexicon.sqlite "$BHF_LEXICAL_DATABASE_PATH"
fi

exec "$@"
