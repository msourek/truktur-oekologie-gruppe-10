#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export STOCKERAU_DATA_DIR="${STOCKERAU_DATA_DIR:-${ROOT_DIR}/.render_data}"
export STOCKERAU_ALLOW_GEOMETRY_ONLY="${STOCKERAU_ALLOW_GEOMETRY_ONLY:-1}"
exec python -m uvicorn stage5_app.app:app --host 0.0.0.0 --port "${PORT:-10000}" --proxy-headers --forwarded-allow-ips="*"