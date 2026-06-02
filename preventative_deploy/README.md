# Preventative Deploy — Policy-as-Code Gated Infrastructure

Automated infrastructure builds (**Terraform**) with **policy-as-code enforcement**
(**OPA/Conftest**) that blocks non-compliant infrastructure *before* it is ever
provisioned.

The entire demo runs **offline with zero AWS cost** — the Terraform plan is
generated with dummy credentials and `-refresh=false`, so it makes no AWS API
calls. It produces the same result every time.

## The idea: shift enforcement left

Most teams *detect* misconfigurations after resources exist (audit scripts,
Config rules). This project enforces the **same standards preventively**, at the
pull-request stage, so a non-compliant change never merges or applies.

```
        write infra (Terraform)
                 │
                 ▼
        terraform plan  ──►  plan.json
                 │
                 ▼
        OPA / Conftest policy gate
            ┌────────────┴────────────┐
        compliant                  violation
        exit 0 ✅                  exit 1 ❌  (PR blocked, with reasons)
```

Three controls, enforced at three stages — defense in depth:

| Control | Preventive (this project) | Detective (sibling tools) |
|---------|---------------------------|---------------------------|
| Required tags (`owner`, `environment`, `cost-center`) | OPA policy on the plan | `automations/tag_compliance` |
| Encryption / public exposure | OPA policy on the plan | `automations/s3_hygiene` |
| No security group open to `0.0.0.0/0` | OPA policy on the plan | `automations/security_posture` |

## What's enforced

The policy (`policy/terraform.rego`) denies a plan that contains any of:

1. A resource missing a required tag (`owner`, `environment`, `cost-center`).
2. An S3 bucket with no server-side encryption.
3. An S3 bucket without a fully-enabled public access block.
4. A security group allowing ingress from `0.0.0.0/0`.

## Layout

```
preventative_deploy/
├── terraform/
│   ├── main.tf            # VPC + security group + S3 (encryption, public-access block)
│   ├── variables.tf
│   ├── compliant.tfvars   # passes every policy
│   └── violation.tfvars   # breaks every policy on purpose
├── policy/
│   ├── terraform.rego     # the policy gate (custom org + security rules)
│   └── terraform_test.rego# policy unit tests (conftest verify)
├── demo.sh                # plan offline -> show -json -> conftest gate
└── ci/policy-gate.yml     # GitHub Actions; copy to .github/workflows/ to activate
```

## Prerequisites

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform conftest
```

(No AWS account or credentials required.)

## Run it

```bash
# Policy unit tests — proves the policies themselves are correct
conftest verify -p policy

# Compliant infrastructure passes the gate (exit 0)
./demo.sh compliant

# Non-compliant infrastructure is blocked with clear reasons (exit 1)
./demo.sh violation
```

### Sample output — the gate blocking a bad change

```
$ ./demo.sh violation
==> terraform init
==> terraform plan [violation]  (offline: dummy creds + -refresh=false)
==> conftest policy gate

FAIL - plan.json - main - aws_s3_bucket.data (bucket "demo-violation-bucket-0001") has no server-side encryption
FAIL - plan.json - main - aws_s3_bucket.data (bucket "demo-violation-bucket-0001") is missing a fully-enabled public access block
FAIL - plan.json - main - aws_s3_bucket.data is missing required tag 'cost-center'
FAIL - plan.json - main - aws_s3_bucket.data is missing required tag 'environment'
FAIL - plan.json - main - aws_security_group.web allows ingress from 0.0.0.0/0 on port 443
FAIL - plan.json - main - aws_vpc.main is missing required tag 'cost-center'
...
9 tests, 0 passed, 9 failures
```

## How it stays free and offline

The AWS provider is configured with dummy credentials and `skip_*` validation
flags, and the plan always runs with `-refresh=false`. With no data sources and
no state refresh, Terraform produces a complete plan without contacting AWS —
so there are no credentials to manage and nothing is ever created or billed.

## CI

`.github/workflows/policy-gate.yml` (at the repo root) runs the policy unit
tests and the compliant gate on every PR that touches `preventative_deploy/`.
It lives at the repo root because GitHub only runs workflows from
`.github/workflows/`.

## Runtime enforcement (kind + Kyverno)

`runtime/` extends the story one layer down: the **same controls** enforced
*inside a cluster* by Kyverno admission control, so a non-compliant workload is
rejected the moment it's applied. It can be checked offline with the Kyverno CLI
(`runtime/demo.sh verify`) or demonstrated live on a local kind cluster
(`runtime/demo.sh up && runtime/demo.sh test`). See `runtime/README.md`.

## Why these design choices

- **Plan JSON, not raw HCL.** Policies evaluate `terraform show -json`, the
  resolved plan — so toggles, variables, and computed values are accurate
  rather than guessed from source.
- **Custom Rego for org policy.** Off-the-shelf scanners (Checkov, tfsec) cover
  security baselines but can't know your tagging taxonomy. Authoring the rules
  in Rego shows that gap being filled — and the two approaches compose: run a
  scanner for breadth and this for org-specific policy.
- **Policies are unit-tested.** `conftest verify` runs `terraform_test.rego`
  against synthetic plans, so the guardrails themselves are tested like code.
