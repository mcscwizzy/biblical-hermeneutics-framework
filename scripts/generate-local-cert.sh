#!/usr/bin/env sh
set -eu

CERT_DIR="${BHF_LOCAL_CERT_DIR:-.bhf/certs}"
CERT_FILE="${CERT_DIR}/localhost.crt"
KEY_FILE="${CERT_DIR}/localhost.key"
FORCE="${BHF_LOCAL_CERT_FORCE:-false}"

if ! command -v openssl >/dev/null 2>&1; then
  echo "OpenSSL is required to generate a local HTTPS certificate." >&2
  exit 1
fi

mkdir -p "$CERT_DIR"

if [ "$FORCE" != "true" ] && { [ -f "$CERT_FILE" ] || [ -f "$KEY_FILE" ]; }; then
  echo "Local certificate files already exist in ${CERT_DIR}."
  echo "Set BHF_LOCAL_CERT_FORCE=true to replace them."
  exit 0
fi

openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 825 \
  -keyout "$KEY_FILE" \
  -out "$CERT_FILE" \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1"

chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo "Generated local HTTPS certificate:"
echo "  ${CERT_FILE}"
echo "  ${KEY_FILE}"
