#!/bin/sh
set -eu
# systemd supplies the private credential as a file, never a command-line argument.
DETECTOR_API_TOKEN=$(cat "${CREDENTIALS_DIRECTORY:?}/api-token")
export DETECTOR_API_TOKEN
exec /home/xslop/venv/bin/python -m uvicorn detector_server.app:create_app \
  --factory --host 127.0.0.1 --port 18767 --workers 1 \
  --no-access-log --no-proxy-headers --limit-concurrency 32 \
  --timeout-keep-alive 5
