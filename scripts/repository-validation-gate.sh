#!/usr/bin/env bash
set -euo pipefail

if [[ "${VALIDATION_RESULT:-}" != "success" ]]; then
  echo '::error::Repository validation did not succeed; merge gate denied.'
  exit 1
fi
echo 'Repository validation passed. This is not custom-controller certification.'
