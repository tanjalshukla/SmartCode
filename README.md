# Semantic Autonomy MVP

A CLI tool (`sc`) that runs a coding agent with intent-first permission gating and dynamic trust leases.

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

## Initialize

```bash
python -m sc init --model-id <inference-profile-arn> --region us-east-1
```

This creates `.sc/config.json` and `.sc/trust.db` in the repo.

## Doctor (verify AWS + Bedrock)

```bash
python -m sc doctor --model-id <inference-profile-arn> --region us-east-1
```

## Run

```bash
python -m sc run "Add a small unit test for function X in foo.py"
```
To show the model's intent and plan before the diff:

```bash
python -m sc run "Add a small unit test for function X in foo.py" --show-intent
```

The flow:
1. The agent emits a strict JSON intent declaration.
2. The agent emits a unified diff patch.
3. The CLI validates the patch (must be within declared files).
4. You approve/deny (and optionally remember) after seeing the diff.
5. The CLI applies the patch only if approved (or auto-approved via leases).

After a file has been approved repeatedly (default 3 times), the CLI can offer to grant
+permanent auto-apply permission for that file. You can override the threshold per run:

```bash
python -m sc run "Update foo.py" --permanent-threshold 5
```

## Leases

```bash
python -m sc leases
python -m sc leases --json
python -m sc revoke path/to/file.py
python -m sc revoke --all
```
Revoking a lease also clears approval history for that file (so the permanent threshold starts over).
Read approvals are permanent once granted (you can revoke them at any time).

## Ask (read-only)

```bash
python -m sc ask "How does the trust DB work?"
python -m sc ask "Explain this module" -f sc/cli.py
```

## Notes

- The tool uses `anthropic[bedrock]` and passes the inference profile ID/ARN as `model`.
- Patches are applied with `git apply` and restricted to declared files.
- You can also set `SA_MODEL_ID` in the environment as a fallback if no config is present.
- File reads are truncated to `read_max_chars` (configurable in `.sc/config.json`) to control cost/latency.
