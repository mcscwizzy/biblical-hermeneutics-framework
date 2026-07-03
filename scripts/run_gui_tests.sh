#!/usr/bin/env bash
set -euo pipefail

pytest tests/gui -m "not slow" "$@"
