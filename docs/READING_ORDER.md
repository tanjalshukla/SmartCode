# Reading Order

## 1) Entry points
1. `sc/__main__.py`
2. `sc/cli.py`
3. `sc/commands/admin.py`
4. `sc/commands/observe.py`

## 2) Core run loop
1. `sc/run/command.py`
2. `sc/run/read_stage.py`
3. `sc/run/model.py`
4. `sc/run/apply_stage.py`
5. `sc/run/ui.py`
6. `sc/run/traces.py`
7. `sc/run/reporting.py`
8. `sc/run/helpers.py`

## 3) Policy + trust
1. `sc/policy.py`
2. `sc/features.py`
3. `sc/plan_gate.py`
4. `sc/prompt_builder.py`
5. `sc/trust_db.py`

## 4) Model protocol + validation
1. `sc/schema.py`
2. `sc/agent_client.py`
3. `sc/checkin_quality.py`
4. `sc/session.py`
5. `sc/session_feedback.py`

## 5) Infra helpers
1. `sc/constraints.py`
2. `sc/verification.py`
3. `sc/patch.py`
4. `sc/repo.py`
5. `sc/config.py`
6. `sc/cli_shared.py`

## 6) Test pass order
1. `tests/test_schema_checkin.py`
2. `tests/test_policy.py` + `tests/test_features.py` + `tests/test_phase.py`
3. `tests/test_constraints.py` + `tests/test_plan_gate.py` + `tests/test_prompt_builder.py`
4. `tests/test_trust_db_*.py`
5. `tests/test_verification.py` + `tests/test_session*.py`
