#!/bin/sh
set -eu

# Apply the current schema before serving requests. This upgrades a persisted
# study database with reviewed archaeology records and media on container start.
if [ -n "${BHF_STUDY_DB_PATH:-}" ]; then
  mkdir -p "$(dirname "$BHF_STUDY_DB_PATH")"
  python -c 'import os; from bhf_agent.study_db import initialize_database; initialize_database(os.environ["BHF_STUDY_DB_PATH"])'
fi

if [ -n "${BHF_LEXICAL_DATABASE_PATH:-}" ] \
  && [ -f /app/.bhf-seed/lexicon.sqlite ]; then
  should_seed=false
  case "${BHF_LEXICAL_SEED_POLICY:-missing}" in
    refresh|replace|always)
      should_seed=true
      ;;
    missing|if-missing)
      if [ ! -f "$BHF_LEXICAL_DATABASE_PATH" ]; then
        should_seed=true
      fi
      ;;
    none|never)
      ;;
    *)
      echo "Invalid BHF_LEXICAL_SEED_POLICY: ${BHF_LEXICAL_SEED_POLICY}" >&2
      echo "Expected one of: missing, refresh, none" >&2
      exit 1
      ;;
  esac

  if [ "$should_seed" = true ]; then
    target_dir="$(dirname "$BHF_LEXICAL_DATABASE_PATH")"
    target_name="$(basename "$BHF_LEXICAL_DATABASE_PATH")"
    tmp_path="${target_dir}/.${target_name}.tmp.$$"
    mkdir -p "$target_dir"
    cp /app/.bhf-seed/lexicon.sqlite "$tmp_path"
    mv "$tmp_path" "$BHF_LEXICAL_DATABASE_PATH"
  fi
fi

if [ -n "${BHF_COMMENTARY_DB_PATH:-}" ] \
  && [ -f /app/.bhf-seed/commentary.sqlite ]; then
  should_seed=false
  case "${BHF_COMMENTARY_SEED_POLICY:-missing}" in
    refresh|replace|always)
      should_seed=true
      ;;
    missing|if-missing)
      if [ ! -f "$BHF_COMMENTARY_DB_PATH" ]; then
        should_seed=true
      fi
      ;;
    none|never)
      ;;
    *)
      echo "Invalid BHF_COMMENTARY_SEED_POLICY: ${BHF_COMMENTARY_SEED_POLICY}" >&2
      echo "Expected one of: missing, refresh, none" >&2
      exit 1
      ;;
  esac

  if [ "$should_seed" = true ]; then
    target_dir="$(dirname "$BHF_COMMENTARY_DB_PATH")"
    target_name="$(basename "$BHF_COMMENTARY_DB_PATH")"
    tmp_path="${target_dir}/.${target_name}.tmp.$$"
    mkdir -p "$target_dir"
    cp /app/.bhf-seed/commentary.sqlite "$tmp_path"
    mv "$tmp_path" "$BHF_COMMENTARY_DB_PATH"
  fi
fi

exec "$@"
