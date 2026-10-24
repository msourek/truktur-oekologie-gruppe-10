#!/usr/bin/env bash
set -euo pipefail

# Render build phase. Install dependencies and stage only the derived project
# inputs that the application needs. The source Rhino 3DM is intentionally not
# copied into the runtime bundle and has no public route.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${STOCKERAU_DATA_DIR:-${ROOT_DIR}/.render_data}"

# The current 3D endpoint reads the original 3DM at runtime. It is copied into
# the private Render runtime only after an explicit setting; the repository remains private.
if [[ "${RENDER_INCLUDE_RHINO_MODEL:-0}" == "1" ]]; then
  INCLUDE_RHINO_MODEL=1
else
  INCLUDE_RHINO_MODEL=0
fi

python -m pip install --upgrade pip
python -m pip install -r "${ROOT_DIR}/requirements.txt"

rm -rf "${DATA_DIR}"
mkdir -p "${DATA_DIR}/api_responses"
if [[ "${INCLUDE_RHINO_MODEL}" == "1" ]]; then
  cp "${ROOT_DIR}/data/Stockerau Rhino Export from RFEM.3dm" "${DATA_DIR}/"
  echo "Original Rhino model copied into private Render runtime (not served as a static file)."
elif [[ "${STOCKERAU_ALLOW_GEOMETRY_ONLY:-1}" == "1" ]]; then
  echo "WARNING: source Rhino model excluded; Render can serve the carbon dashboard, but the interactive model geometry will be unavailable."
else
  echo "ERROR: model omitted and geometry-only mode disabled; app would fail its model endpoint." >&2
  exit 2
fi
cp "${ROOT_DIR}/output/material_assignment_detailed.csv" "${DATA_DIR}/material_assignment_detailed.csv"
cp "${ROOT_DIR}/stage4_independent/stage4_carbon_results.csv" "${DATA_DIR}/stage4_carbon_results.csv"
cp "${ROOT_DIR}"/stage4_independent/api_responses/*.json "${DATA_DIR}/api_responses/"

echo "Render data prepared: Stage 3 assignments + Stage 4 results + ÖKOBAUDAT snapshots."
echo "Original .3dm deliberately not copied."