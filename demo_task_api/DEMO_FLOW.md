# Demo Flow

This flow is optimized for a short research demo and fits a 5-minute video.

Goal:
- show freeform rule authoring before the task starts
- show spec-aware planning
- trigger one strong model-initiated architectural check-in
- give one explicit developer preference
- show that the second session reuses that preference and interrupts less

Do not reset between session 1 and session 2.

## Recommended 5-minute structure

Use this pacing when recording:

1. `0:00-0:45` - freeform rule authoring with `sc rules add`
2. `0:45-2:30` - session 1: spec-aware planning + model-initiated architectural check-in
3. `2:30-3:00` - show persisted preference state with `sc observe preferences`
4. `3:00-4:20` - session 2: reduced interruption on related work
5. `4:20-5:00` - observability close with `sc observe report` or `sc observe traces --limit 10`

If time is tight, skip the optional sanity checks and keep only one observability command at the end.

## Setup

Run from the demo repo:

```bash
cd demo_task_api
git init   # one-time, makes this fixture the Smart Coder repo root
git add .
git commit -m "Initial demo fixture"   # optional but recommended for a clean baseline
sc reset --yes
sc rules add "Never modify files under locked/." --yes
sc rules add "Always check in before modifying task_api/api.py." --yes
sc rules add "Always allow docs/*.md." --yes
sc rules add "Always run tests after editing demo repo files." --yes
sc config set-mode balanced
sc config set-verification-cmd "python -m pytest tests -q"
```

Optional sanity check:

```bash
sc rules constraints
sc rules guidelines
```

What to emphasize while recording:
- `sc rules add` accepts freeform rules
- the model decides whether each rule becomes an enforced constraint or prompt-level guidance
- the CLI validates and persists the result before the coding session starts

Recommended quick rule-authoring beat before session 1:

```bash
sc rules add "Never modify files under locked/."
sc rules add "Only check in for API or schema changes."
sc rules constraints
sc rules guidelines
```

What to say:
- the first rule becomes a CLI-enforced hard constraint
- the second becomes prompt-level guidance instead of a hard rule
- this is the distinction between deterministic governance and behavioral conditioning

If you need a shorter recording cut, show only these two rule-authoring commands:

```bash
sc rules add "Never modify files under locked/."
sc rules add "Only check in for API or schema changes."
```

## Session 1: spec-aware planning + architectural check-in

```bash
sc run \
"Read task_api/api.py, task_api/service.py, and docs/task_api_spec.md. Add support for a summary view of task counts by status while preserving the existing response envelopes and handler signatures unless a change is clearly needed. If there is an API design tradeoff, stop and check in with assumptions and options." \
--spec docs/task_api_spec.md \
--show-intent
```

Recommended responses:
- approve read access for `task_api/api.py`
- approve the plan
- if the model asks whether to extend the existing list route or add a dedicated summary path, choose the dedicated path and paste:

```text
Add a dedicated summary path. Do not change the existing list response envelope or handler signatures. Continue autonomously for low-risk internal changes; only check in for API, signature, schema, or security changes.
```

- approve the apply step

What to emphasize while recording:
- the plan is grounded in the spec
- the model surfaces a real API design fork instead of silently guessing
- you are shaping future autonomy with explicit preference feedback

After the run, note the printed `Session id=...` and export it:

```bash
sc observe export --session-id <SESSION_1_ID> --out .sc/exports/session1
```

## Session 2: show learned preference and reduced interruption

Inspect the learned preference state first:

```bash
sc observe preferences
```

Then run the follow-up task:

```bash
sc run \
"Using the same spec, add optional priority filtering and tighten validation messaging while preserving response envelopes and handler signatures. Continue autonomously for low-risk changes and only check in if an API or interface change is required." \
--spec docs/task_api_spec.md \
--show-intent
```

Expected outcome:
- fewer unnecessary check-ins than session 1
- preserved response envelope
- preserved handler signatures
- continued autonomy on service-layer and validation work
- any remaining check-in should be at the API/interface level

After the run, export again:

```bash
sc observe export --session-id <SESSION_2_ID> --out .sc/exports/session2
```

## Close the demo

Show one or two observability commands:

```bash
sc observe report
sc observe traces --limit 10
```

If you want one deeper view:

```bash
sc observe checkin-stats
```

## What the audience should take away

Before coding:
- Smart Coder can compile freeform natural-language rules into either hard constraints or behavioral guidance
- hard constraints and soft guidance are deliberately separated

Session 1:
- the model is spec-aware
- the model can initiate a useful architectural check-in
- the CLI still governs the risky surface

Session 2:
- the system did not just store traces; it reused them
- the previous preference changed how the model and policy behaved
- autonomy increased selectively, not blindly

## Evidence to keep

Export both sessions:

```bash
sc observe export --session-id <SESSION_1_ID> --out .sc/exports/session1
sc observe export --session-id <SESSION_2_ID> --out .sc/exports/session2
```

Capture these screenshots:
- one `sc rules add ...` hard constraint example
- one `sc rules add ...` behavioral-guideline example
- the spec-aware intent summary
- the model-initiated architectural check-in
- `sc observe preferences` before session 2
- one observability close (`sc observe report` or `sc observe traces --limit 10`)

Small numbers to pull into the paper:
- rules compiled to hard constraints
- rules compiled to behavioral guidance
- model-initiated check-ins in session 1
- policy-initiated check-ins in session 1
- total check-ins in session 2
