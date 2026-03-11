# Demo Task API

This is a small task-tracking API fixture for Smart Coder demos.

It is intentionally small, but it has enough structure to show:
- spec-aware planning
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
sc reset --yes
sc rules add "Never modify files under locked/." --yes
sc rules add "Always check in before modifying task_api/api.py." --yes
sc rules add "Always allow docs/*.md." --yes
sc rules add "Always run tests after editing demo repo files." --yes
sc config set-mode balanced
sc config set-verification-cmd "python -m pytest tests -q"
```

Then:
- run the two-session flow in `DEMO_FLOW.md`
