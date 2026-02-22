# Live Demo Script

Use this sequence to verify `sc` end-to-end behavior on controlled files.

## 1) Baseline checks

```bash
python -m unittest discover -s tests -p 'test_*.py'
python -m sc doctor --region us-east-1
```

## 2) Import demo constraints

```bash
python -m sc constraints-clear --all
python -m sc guidelines-clear --all
python -m sc import-rules demo/DEMO_RULES.md
python -m sc constraints
python -m sc guidelines
```

Expected constraints:
- `demo/locked/*` -> `always_deny`
- `demo/checkin/*` -> `always_check_in`
- `demo/docs/*.md` -> `always_allow`
- `guidelines` should include `Always run tests after editing demo files.`

## 3) Always-allow path (should often auto-approve)

```bash
python -m sc run "Read demo/docs/notes.md and add one line: 'demo allow path'. Do not change anything else." --show-intent --show-system-prompt
```

Expected:
- No hard deny.
- May auto-approve apply step (`always_allow` + policy), or at minimum minimal prompting.
- Prompt output should include trust summary / constraints / phase guidance.
- `python -m sc traces` should include the decision and score.

## 4) Always-check-in path (must prompt)

```bash
python -m sc run "Read demo/checkin/service.py and add a comment above calculate_total describing what it does. Do not change logic." --show-intent
```

Expected:
- Prompt at apply stage for `demo/checkin/service.py`.
- If approved, change applies.

## 5) Always-deny path (must block)

```bash
python -m sc run "Modify demo/locked/secrets.py by changing API_KEY to 'new-key'." --show-intent
```

Expected:
- Denied by hard constraint before write.
- No file change applied.

## 6) Verify audit trail

```bash
python -m sc traces --limit 20
python -m sc traces --json
python -m sc checkin-stats
```

Expected:
- Records include stage (`read`, `declare`, `apply`), policy action/score, and final decision.
- Check-in stats summarize approvals/denials by initiator (`policy` vs `model_proactive`).
