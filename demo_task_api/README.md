# Demo Task API

This is a small task-tracking API fixture for Smart Coder demos.

It is intentionally small, but it has enough structure to show:
- freeform rule authoring into hard constraints vs prompt guidance
- spec-aware planning from an explicit task contract
- interface-sensitive changes in `task_api/api.py`
- model-initiated architectural check-ins
- preference learning across sessions
- safety boundaries via `locked/`

Main files:
- `task_api/api.py` - route handlers and response envelopes
- `task_api/service.py` - business logic and validation
- `task_api/store.py` - in-memory task store
- `task_api/errors.py` - structured application errors
- `docs/task_api_spec.md` - task constraints for the demo
- `DEMO_FLOW.md` - full demo script, including evidence capture

## Run this Demo with Smart Coder

From this directory:

```bash
git init   # one-time, if this fixture is not already its own repo
git rev-parse --show-toplevel   # should print .../demo_task_api
sc reset --yes
sc rules constraints-clear --all
sc rules guidelines-clear --all
sc config set-mode balanced
```

Then:
- run the two-session flow in `DEMO_FLOW.md`
- if verification is not already configured, use the operator bootstrap in `../docs/OPERATOR_RUNBOOK.md`
