# Runtime Enforcement — kind + Kyverno

The runtime half of the story: the same governance, but enforced **inside the
cluster** by **Kyverno** admission control. A non-compliant workload is
**rejected the moment it's applied** — it never starts.

This mirrors the Terraform gate one layer down: build-time policy stops bad
*infrastructure*; runtime policy stops bad *workloads*.

## What's enforced

| Policy | Rejects a workload that… | Mirrors |
|--------|--------------------------|---------|
| `require-org-labels` | is missing `owner`, `environment`, or `cost-center` labels | the tag controls |
| `disallow-privileged` | runs a privileged container | the security baseline |
| `require-resource-limits` | has no CPU/memory limits | cost/stability hygiene |

All policies match `Pod`; Kyverno **autogen** automatically extends them to
Deployments and other pod controllers (you'll see the generated
`autogen-*` rules acting on `spec/template/...`).

## Two ways to run

### 1. Offline — no Docker, no cluster (great for CI)

The Kyverno CLI evaluates the policies against the manifests using the same
engine as admission control:

```bash
brew install kyverno
./demo.sh verify
```

Expected: the compliant workload passes 3 rules; the violation fails 3.

### 2. Live — the "reject a bad pod" moment

```bash
brew install kind kubernetes-cli          # plus Docker running
./demo.sh up      # kind cluster + Kyverno + policies (~2 min, pulls images)
./demo.sh test    # compliant is created; violation is REJECTED at apply time
./demo.sh down    # tear the cluster down
```

The `test` step is the demo highlight — `kubectl apply` of the violation returns
an admission error like:

```
Error from server: admission webhook "validate.kyverno.svc-fail" denied the request:

resource Deployment/default/violation-app was blocked due to the following policies:

disallow-privileged:
  no-privileged-containers: Privileged containers are not allowed.
require-org-labels:
  require-owner-env-costcenter: 'Missing required labels: owner, environment, cost-center.'
require-resource-limits:
  require-cpu-memory-limits: CPU and memory limits are required on every container.
```

## Layout

```
runtime/
├── policies/
│   ├── require-org-labels.yaml
│   ├── disallow-privileged.yaml
│   └── require-resource-limits.yaml
├── workloads/
│   ├── compliant.yaml     # accepted
│   └── violation.yaml     # rejected (breaks all three)
└── demo.sh                # verify | up | test | down
```

## Talking points

- **Same controls, three stages:** PR-time (Terraform + OPA), build-time
  (Terraform), and **runtime (Kyverno admission)** — defense in depth.
- **Policies are testable without a cluster** (`kyverno apply` / `./demo.sh
  verify`), so they can gate a PR in CI before they ever reach a cluster.
- **Autogen** means you write one Pod rule and it covers every controller —
  less policy to maintain.
- `validationFailureAction: Enforce` makes violations hard failures; switch to
  `Audit` to roll out a policy in report-only mode first.
