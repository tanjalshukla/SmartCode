# Live Demo Commands (~5 min)

## Pre-demo

```bash
git restore demo/checkin/service.py demo/feature.py demo/docs/notes.md
rm -f demo/two_sum.py demo/test_two_sum.py
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
aws sso login --profile dev
python -m sc rules constraints-clear --all
python -m sc rules guidelines-clear --all
python -m sc observe revoke --all
python -m sc config set-threshold 1
python -m sc config set-verification-cmd "python -m py_compile demo/feature.py demo/checkin/service.py"
```

## 1. Rule import

```bash
python -m sc rules import demo/DEMO_RULES.md
python -m sc rules constraints
python -m sc rules guidelines
```

## 2. Multi-file task

```bash
python -m sc run \
"Read demo/checkin/service.py, demo/feature.py, and demo/docs/notes.md. Improve the code quality across these files: add input validation where missing, extract any repeated logic into helpers. Keep changes minimal and pythonic. If there is an architecture tradeoff, check in with options." \
--show-intent
```

Replies: read `a`, plan `a`, apply `r`

## 3. Autonomy scaling

```bash
python -m sc observe leases
```

```bash
python -m sc run \
"Update demo/feature.py only: keep greet behavior unchanged but add a concise docstring and tighten input validation error text. Do not modify any other file." \
--show-intent
```

## 4. Safety boundary

```bash
python -m sc run \
"Read demo/locked/secrets.py and set API_KEY='new-key'." \
--show-intent
```

## 5. Feedback shaping autonomy

```bash
python -m sc observe preferences
```

```bash
python -m sc run \
"Read demo/checkin/service.py and demo/feature.py. Improve validation and refactor repeated logic while preserving function signatures and behavior. If there is a meaningful architecture choice, ask one check-in with options." \
--show-intent 
```

Replies:
- read `a`
- plan `a`
- if model check-in appears, pick `1` (or `2`) and in optional guidance paste:
  `For low-risk refactors in demo/checkin and demo/feature, proceed autonomously without check-ins. Only check in for API/signature/schema/security changes.`
- apply `a` or `r`

```bash
python -m sc run \
"Read demo/checkin/service.py and demo/feature.py. Apply one more cleanup pass (naming/docstrings/internal helper extraction) with no API/signature/schema changes." \
--show-intent
```

Expected: fewer model check-ins than prior run (possibly none), and more auto-approval via adaptive policy.

```bash
python -m sc observe preferences
python -m sc observe checkin-stats
python -m sc observe traces --limit 20
```

Optional guideline demo:

```bash
python -m sc run \
"Read demo/checkin/service.py and refactor calculate_total to accept an optional discount_rate parameter." \
--show-intent
```

Replies: read `a`, apply `d`, feedback:
`do not change function signatures in service files, downstream consumers depend on the current interface`

```bash
python -m sc run \
"Read demo/checkin/service.py and change calculate_total to accept an optional tax_rate parameter with a default value." \
--show-intent --show-system-prompt
```

Replies: read `a`, apply `d`, same feedback text.

```bash
python -m sc rules guidelines-suggest --min-count 2
python -m sc rules guidelines-suggest --min-count 2 --apply
python -m sc rules guidelines
```

Payoff run (show learned guideline influence):

```bash
python -m sc run \
"Read demo/checkin/service.py and improve calculate_total robustness and readability with minimal internal changes." \
--show-intent --show-system-prompt
```

Expected: model avoids function-signature changes and sticks to internal logic improvements.

## 6. Observability

```bash
python -m sc report
python -m sc observe checkin-stats
python -m sc observe traces --limit 10
python -m sc observe explain <trace_id_from_traces>
python -m sc report --json | python3 -m json.tool | head -30
```

## If time permits

```bash
python -m sc observe revoke demo/feature.py
python -m sc observe leases
```
