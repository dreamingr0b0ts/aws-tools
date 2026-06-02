#!/usr/bin/env bash
# Build infrastructure as code and enforce org + security policy BEFORE any
# provisioning happens. The plan is generated with dummy credentials and
# -refresh=false, so this makes ZERO AWS calls and costs nothing.
#
# Usage: ./demo.sh [compliant|violation]   (default: compliant)
set -euo pipefail
cd "$(dirname "$0")"

PROFILE="${1:-compliant}"
[ -f "terraform/${PROFILE}.tfvars" ] || {
  echo "unknown profile '${PROFILE}' (use: compliant | violation)" >&2
  exit 2
}

echo "==> terraform init"
terraform -chdir=terraform init -input=false -no-color >/dev/null

echo "==> terraform plan [${PROFILE}]  (offline: dummy creds + -refresh=false)"
terraform -chdir=terraform plan -input=false -refresh=false -no-color \
  -var-file="${PROFILE}.tfvars" -out=tf.plan >/dev/null
terraform -chdir=terraform show -json tf.plan > plan.json

echo "==> conftest policy gate"
echo
conftest test plan.json
