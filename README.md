# Semantic Autonomy MVP

`sc` is a governance-first coding agent CLI.  
The model proposes; the CLI enforces.

Core design:
- untrusted model with strict JSON protocol
- local policy and constraint enforcement
- trace-backed adaptive autonomy
- explicit read/apply checkpoints when risk is high

## Prerequisites

- Python 3.11+
- AWS IAM Identity Center (SSO) configured
- Bedrock access to a Claude inference profile (ID/ARN)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

```bash
python -m sc init --model-id <inference-profile-arn> --region us-east-1
python -m sc doctor --model-id <inference-profile-arn> --region us-east-1
python -m sc run "Add a small unit test for function X in foo.py" --show-intent
```

This creates local state in `.sc/config.json` and `.sc/trust.db`.

## Command Groups

- `python -m sc config ...` config updates (`set-mode`, `set-verification-cmd`)
- `python -m sc rules ...` import/manage hard constraints and guidelines
- `python -m sc observe ...` traces, leases, explainability, stats, preferences

Legacy top-level aliases still work for compatibility.

## Core Workflows

Run with intent visibility:

```bash
python -m sc run "Update foo.py and add tests" --show-intent
```

Inspect live policy state:

```bash
python -m sc observe leases
python -m sc observe traces --limit 20
python -m sc observe report
```

Import rules from AGENTS/CLAUDE-style files:

```bash
python -m sc rules import demo/DEMO_RULES.md
python -m sc rules constraints
python -m sc rules guidelines
```

Set autonomy mode:

```bash
python -m sc config set-mode balanced
python -m sc config set-mode milestone
```

Reset learned autonomy preferences:

```bash
python -m sc observe preferences-clear --yes
```

Export the latest session bundle for analysis:

```bash
python -m sc observe export --out .sc/exports
```

## Enforcement Semantics

- Constraint precedence: `always_deny` > `always_check_in` > `always_allow`
- Phase gates:
  - research: no writes
  - planning: markdown-only writes
  - implementation/review: writes allowed under policy
- Apply is all-or-nothing: writes are staged and atomically replaced per file; failures abort with cleanup.

## Testing

```bash
python -m pytest tests -q
```

## Demo

- Copy-paste demo script: `demo/DEMO_COMMANDS.md`
- Operator steps: `docs/OPERATOR_RUNBOOK.md`

## Notes

- Bedrock model ID can be set via `--model-id` or `SA_MODEL_ID`.
- Read context is truncated by `read_max_chars` in `.sc/config.json`.
- Numeric policy knobs remain in `.sc/config.json`, but the normal user-facing control is `autonomy_mode`.
