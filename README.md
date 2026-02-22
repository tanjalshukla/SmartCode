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
To make the adaptive prompt visible (trust summary + constraints + phase guidance):

```bash
python -m sc run "Add a small unit test for function X in foo.py" --show-system-prompt
```
To update the permanent approval threshold:

```bash
python -m sc set-threshold 3
```

The flow:
1. The agent emits a strict JSON intent declaration.
2. The agent may request file reads; read approvals are remembered permanently.
3. The agent emits file updates, and the CLI renders a unified diff.
4. The CLI enforces phase gates (`research`: no writes, `planning`: `.md`-only writes), validates file scope, enforces hard constraints, and evaluates adaptive check-in policy.
5. You approve/deny only when required; otherwise apply auto-approves with trace logging.

After a file has been approved repeatedly (default 3 times), the CLI can offer to grant
permanent auto-apply permission for that file. You can override the threshold per run:

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

## Hard Constraints (AGENTS/CLAUDE import)

```bash
python -m sc import-rules demo/DEMO_RULES.md
python -m sc import-rules path/to/CLAUDE.md path/to/rules.md
python -m sc constraints
python -m sc constraints --json
python -m sc guidelines
python -m sc guidelines --json
python -m sc guidelines-clear --source demo/DEMO_RULES.md
python -m sc guidelines-clear --all
python -m sc constraints-clear --source demo/DEMO_RULES.md --pattern "*"
python -m sc constraints-clear --all
```

Imported constraints support:
- `always_deny`
- `always_check_in`
- `always_allow`

Constraint precedence is strict: `always_deny` > `always_check_in` > `always_allow`.

## Traces (policy instrumentation)

```bash
python -m sc traces
python -m sc traces --limit 50
python -m sc traces --json
python -m sc checkin-stats
python -m sc checkin-stats --json
```

The trace log captures governance checkpoints (read/intent/apply), policy score/action, final decision,
and check-in initiator attribution (`policy` vs `model_proactive`).

## Ask (read-only)

```bash
python -m sc ask "How does the trust DB work?"
python -m sc ask "Explain this module" -f sc/cli.py
```

## Testing

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Demo Scenario

Use `demo/README.md` for a guided end-to-end validation run (constraints, policy decisions, traces).

## Notes

- The tool uses `anthropic[bedrock]` and passes the inference profile ID/ARN as `model`.
- You can also set `SA_MODEL_ID` in the environment as a fallback if no config is present.
- File reads are truncated to `read_max_chars` (configurable in `.sc/config.json`) to control cost/latency.
- Adaptive policy settings are configurable in `.sc/config.json` (`adaptive_policy_enabled`, `policy_proceed_threshold`, `policy_flag_threshold`).
- Policy risk features include security-sensitive path/content detection and heuristic change-pattern classification.
- If a rule line is ambiguous during `import-rules`, it is preserved as a behavioral guideline and flagged as ambiguous.
- The system prompt has two layers: slower trust/constraint context (rebuilt on phase changes) and fast session feedback (updated before each model call).
