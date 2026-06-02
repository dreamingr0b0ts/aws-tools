#!/usr/bin/env bash
# Runtime enforcement demo: Kyverno admission control rejects non-compliant
# workloads. Same governance as the Terraform gate, enforced inside the cluster.
#
# Usage:
#   ./demo.sh verify   # OFFLINE policy check via the Kyverno CLI (no cluster/Docker)
#   ./demo.sh up       # create a local kind cluster, install Kyverno, apply policies
#   ./demo.sh test     # apply compliant (accepted) then violation (REJECTED live)
#   ./demo.sh down     # delete the kind cluster
#
# verify needs only the `kyverno` CLI. up/test/down need Docker + kind + kubectl.
set -euo pipefail
cd "$(dirname "$0")"

CLUSTER=preventative-demo
KYVERNO_VER="${KYVERNO_VER:-v1.18.1}"

case "${1:-verify}" in
  verify)
    echo "== COMPLIANT (expect pass) =="
    kyverno apply policies/ --resource workloads/compliant.yaml
    echo "== VIOLATION (expect failures) =="
    kyverno apply policies/ --resource workloads/violation.yaml || true
    ;;
  up)
    kind get clusters 2>/dev/null | grep -qx "$CLUSTER" \
      || kind create cluster --name "$CLUSTER" --wait 90s
    kubectl apply -f "https://github.com/kyverno/kyverno/releases/download/${KYVERNO_VER}/install.yaml"
    kubectl -n kyverno rollout status deploy/kyverno-admission-controller --timeout=180s
    sleep 10  # allow admission webhooks to register
    kubectl apply -f policies/
    echo
    echo "Cluster ready with policies. Run './demo.sh test'."
    ;;
  test)
    echo "== COMPLIANT workload (expect: created) =="
    kubectl apply -f workloads/compliant.yaml
    echo
    echo "== VIOLATION workload (expect: REJECTED by Kyverno) =="
    kubectl apply -f workloads/violation.yaml \
      && echo "!! unexpectedly admitted" \
      || echo ">> blocked by Kyverno (as intended)"
    ;;
  down)
    kind delete cluster --name "$CLUSTER"
    ;;
  *)
    echo "usage: $0 [verify|up|test|down]" >&2
    exit 2
    ;;
esac
