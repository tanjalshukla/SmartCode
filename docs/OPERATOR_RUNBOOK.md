# Operator Runbook

This runbook is for running `sc` reliably in demos, lab sessions, and internal studies.

## 1) Session Bootstrap

```bash
source .venv/bin/activate
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
aws sso login --profile dev
```

Verify account + Bedrock:

```bash
AWS_PROFILE=dev python -m sc doctor --model-id <inference-profile-arn> --region us-east-1
```

## 2) Clean Baseline (Recommended Before Every Study Session)

```bash
git restore demo/checkin/service.py demo/feature.py demo/docs/notes.md
python -m sc rules constraints-clear --all
python -m sc rules guidelines-clear --all
python -m sc observe revoke --all
python -m sc observe preferences-clear --yes
python -m sc config set-threshold 1
python -m sc config set-verification-cmd ".venv/bin/python -m py_compile demo/feature.py demo/checkin/service.py"
python -m sc rules import demo/DEMO_RULES.md
```

## 3) Standard Demo Flow

1. Import + inspect rules:
   - `python -m sc rules constraints`
   - `python -m sc rules guidelines`
2. Run multi-file task:
   - `python -m sc run "<task>" --show-intent`
3. Show adaptive state:
   - `python -m sc observe leases`
   - `python -m sc observe traces --limit 20`
4. Show safety block:
   - attempt read/write under `demo/locked/*`
5. Show observability:
   - `python -m sc observe report`
   - `python -m sc observe checkin-stats`

Use `demo/DEMO_COMMANDS.md` for a paste-ready script.

## 4) Common Failures and Recovery

### `ExpiredToken` / Bedrock 403
Cause: stale session credentials.

Fix:
```bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
aws sso login --profile dev
AWS_PROFILE=dev python -m sc doctor --model-id <inference-profile-arn> --region us-east-1
```

### `could not resolve credentials from session`
Cause: stale environment overrides.

Fix: same as above; ensure `AWS_PROFILE=dev` is set for command execution.

### Model output fails schema validation
Cause: non-JSON or malformed check-in payload.

Fix:
- rerun task once
- add tighter task wording
- keep `--show-intent` for visibility

## 5) Lab Study Hygiene

- Start each participant with cleared leases/preferences (`revoke --all`, `preferences-clear --yes`).
- Keep the same verification command across sessions.
- Export traces after each session:

```bash
python -m sc observe traces --limit 500 --json > traces_session.json
python -m sc observe report --json > report_session.json
```

## 6) Post-Session Reset

```bash
git restore demo/checkin/service.py demo/feature.py demo/docs/notes.md
python -m sc observe revoke --all
python -m sc observe preferences-clear --yes
```
