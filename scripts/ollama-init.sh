#!/bin/sh
set -eu

MODEL="${OLLAMA_MODEL:-qwen2.5:0.5b}"

echo "Waiting for Ollama at ${OLLAMA_HOST:-http://ollama:11434}..."
until ollama list >/dev/null 2>&1; do
  sleep 2
done

if ollama list 2>/dev/null | awk 'NR > 1 { print $1 }' | grep -Fxq "$MODEL"; then
  echo "Model already present: $MODEL"
  exit 0
fi

echo "Pulling model: $MODEL"
ollama pull "$MODEL"
