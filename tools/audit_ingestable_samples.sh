#!/usr/bin/env bash
set -euo pipefail

# Run strict SWIM audit only on curated ingestable sample payloads.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

python "${REPO_ROOT}/tools/audit_swim_messages.py" \
  "${REPO_ROOT}/Sample XML/Ingestable" \
  --strict \
  --fail-on-unroutable
