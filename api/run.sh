#!/usr/bin/env bash
cd "$(dirname "$0")/.."
exec .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port ${NE_PORT:-8099}
