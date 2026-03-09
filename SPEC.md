# AdaptiveAuth

A CLI governance layer between a developer and an LLM coding agent. It learns when to pause and ask the developer vs. when to proceed autonomously, adapting over time to each developer's implicit preferences.

The model is untrusted. It proposes actions; the CLI enforces all reads, writes, and check-ins. Trust is built from interaction traces — approval history, correction patterns, review timing — not from the model's self-assessment. The model participates in oversight by reasoning about its own uncertainty and surfacing architectural decisions, but the CLI makes the final call.

This targets skilled engineers who plan, supervise, and validate. The goal: supervision gets more efficient over time because the system learns what this particular developer actually cares about.

---

# Part 1: Technical Implementation

## Architecture

Check-ins come from two independent sources:

1. **CLI policy engine** — evaluates trust scores, file features, constraints, session state. Decides auto-approve vs. check-in vs. deny. Runs regardless of what the model does.
2. **Model system prompt** — the model is told its trust context and instructed to reason about uncertainty. It pauses for architectural decisions, approach tradeoffs, plan deviations. Does not pause for file permissions or routine implementation.

Either side can trigger a check-in independently. Both are logged with `check_in_initiator` so we can learn which source is better calibrated over time.

```
┌─────────────────────────────────────────────────────┐
│                    Developer                         │
│  (terminal / IDE / reviews async queue)              │
└──────────────────────┬──────────────────────────────┘
                       │ commands, approvals, corrections
                       ▼
┌─────────────────────────────────────────────────────┐
│                 AdaptiveAuth CLI                     │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  Governance  │  │   Policy     │  │   Trace    │ │
│  │  Engine      │←─│   Engine     │  │   Logger   │ │
│  │ - validates  │  │  (check-in   │  │  (records   │ │
│  │   diffs      │  │   vs. auto)  │  │   every    │ │
│  │ - enforces   │  │              │  │   decision │ │
│  │   scope      │  │ CLI-SIDE     │  │   + who    │ │
│  │ - hash check │  │ CHECK-INS    │  │   started  │ │
│  └─────────────┘  └──────────────┘  │   it)      │ │
│         │              ▲            └────────────┘  │
│         │              │ features         │          │
│         │         ┌────┴─────────┐        │ traces   │
│         │         │  Trust DB    │◄───────┘          │
│         │         │  (SQLite)    │                   │
│         │         └──────────────┘                   │
│         ▼                                            │
│  ┌──────────────────────────────────────────────┐   │
│  │   AGENTS.md / CLAUDE.md parser               │   │
│  │   (imports static rules as hard constraints) │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │   System prompt builder                      │   │
│  │   (injects trust context into model prompt)  │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────┘
                       │ governed API calls + system prompt
                       ▼
┌─────────────────────────────────────────────────────┐
│              LLM Agent (untrusted)                   │
│                                                     │
│  MODEL-SIDE CHECK-INS:                              │
│  Pauses for: architectural decisions, approach      │
│  tradeoffs, plan deviations, phase transitions,     │
│  low confidence on design intent.                   │
│                                                     │
│  Does NOT pause for: file permissions, routine      │
│  implementation, style choices.                     │
│                                                     │
│  Communicates via structured JSON protocol:         │
│  read_request, intent_declaration, file_update,     │
│  check_in_message, plan_revision                    │
└─────────────────────────────────────────────────────┘
```

## 4-Stage Pipeline

Every task flows through:

1. **Intent declaration** (`run/command.py`) — model produces a structured plan listing files to read and modify.
2. **Read stage** (`run/read_stage.py`) — each read request goes through the approval cascade. Approved files are loaded into context.
3. **Generate updates** (`run/model.py`) — model generates code changes. Can initiate proactive check-ins during generation.
4. **Apply + verify** (`run/apply_stage.py`) — each write goes through the approval cascade. Approved writes use atomic two-phase file writes (temp + `os.replace`). Verification runs post-write.

## Approval Cascade

For every file access, evaluated in order:

1. **Hard constraints** — permanent rules (always_deny, always_check_in, always_allow). Override everything.
2. **Active leases** — temporary trust grants from prior approvals. Auto-approve for the session.
3. **Adaptive policy** (`policy.py`) — computes a score from weighted signals, compared against thresholds.
4. **Threshold adaptation** (`autonomy.py`) — thresholds shift based on learned preferences and check-in calibration.

## Policy Engine

Heuristic scoring from `policy.py`. All weights are initial guesses — lab studies will produce data to replace them with learned values.

**Signals and weights (actual implementation):**

| Category | Signal | Weight | Notes |
|----------|--------|--------|-------|
| History | Prior approvals (rubber-stamp-discounted) | +0.4 per | Rubber-stamps <5s count as 0.5x |
| History | Prior denials | -0.7 per | |
| History | Deliberate review pace (>15s) | +0.15 | |
| History | High edit distance | -0.5 max | Developer heavily corrects output |
| Risk | Large diff (>80 lines) | -0.8 | |
| Risk | Medium diff (>30 lines) | -0.4 | |
| Risk | Blast radius >3 files | -0.8 | |
| Risk | Large multi-file action (>4) | -0.9 | |
| Risk | Multi-file action (>1) | -0.35 | |
| Risk | New file | -0.6 | |
| Risk | Security sensitive | -2.0 | Path/content keyword detection |
| Risk | API/data model change | -0.8 | |
| Risk | Config change | -0.4 | |
| Risk | Dependency update | -0.5 | |
| Risk | Test/documentation | +0.3 | Low impact |
| Risk | Error handling | +0.1 | Usually localized |
| Session | Recent denials | -0.7 per (max 3) | |
| Quality | Verification failure rate >30% | -0.6 | From trace history |
| Quality | Low model confidence (<0.40, 3+ samples) | -0.3 | From trace history |

**Internal thresholds (hidden from the normal user UX):**
- Score >= 0.9 → `proceed` (auto-approve silently)
- Score >= 0.2 → `proceed_flag` (approve, flag for summary)
- Score < 0.2 → `check_in` (ask the user)

These numeric thresholds remain implementation details. Lab participants should interact with qualitative autonomy modes and reason strings, not raw scores.

## User-Facing Autonomy Modes

For lab studies and product UX, the user should control autonomy through one qualitative setting instead of threshold tuning:

- `strict` — conservative approvals, heavier plan gating, more milestone check-ins.
- `balanced` — default mode; risk-aware with moderate autonomy.
- `milestone` — minimize routine interruptions, but always check in at milestone boundaries and meaningful design pivots.
- `autonomous` — proceed aggressively on low-risk routine work; still stop on hard constraints, security, interface changes, or verification failures.

Modes compile down to internal thresholds and plan-gate behavior. The numeric policy remains active, but it is not part of the normal user-facing API.

**Threshold adaptation** (`autonomy.py::adjusted_policy_thresholds`):
- User prefers fewer check-ins → thresholds drop by 0.25 (+ 0.10 if topic-scoped)
- Model check-in approval rate <40% (5+ samples) → thresholds rise by 0.15
- Floor clamp at -0.5 to prevent nonsensical values

## Preference Learning

When the user gives feedback at any approval point, the text goes to the model via `summarize_autonomy_feedback()` which returns structured JSON. No regex parsing — the model classifies intent into 4 preference fields:

- `prefer_fewer_checkins` (boolean)
- `allowed_checkin_topics` (subset of: api, signature, schema, security, architecture, config, test, deployment)
- `skip_low_risk_plan_checkpoint` (boolean)
- `scoped_paths` (file path patterns where preferences apply)

Preferences merge additively (OR for booleans, UNION for collections) and persist in SQLite. They directly influence threshold adaptation.

## Behavioral Guidelines

When the system sees repeated denial feedback on the same pattern, `guideline_candidates()` drafts permanent prompt injections (e.g., "Use AppError with error codes, not generic Error"). Accepted guidelines go into the system prompt. The model never writes its own rules — the CLI detects patterns, drafts suggestions, the developer confirms.

## Database Schema

SQLite with 8 tables:

| Table | Purpose |
|-------|---------|
| `leases` | Temporary write trust grants (repo_root, file_path, expires_at, source) |
| `read_leases` | Temporary read trust grants (same structure) |
| `decisions` | High-level approval records (task, approved, planned/touched files) |
| `decision_traces` | Per-file decision log — 28 columns capturing every signal, decision, and outcome |
| `plan_revisions` | Plan checkpoint history (revision rounds, developer feedback, approval) |
| `hard_constraints` | Permanent rules (path_pattern, read_policy, write_policy, source, overridable) |
| `behavioral_guidelines` | Learned/imported prompt directives (guideline text, source) |
| `autonomy_preferences` | Learned check-in preferences per repo (JSON blob) |

The `decision_traces` table is the primary data source for post-study analysis. It records: stage, action_type, file_path, change_type, diff_size, blast_radius, lease state, approval history, policy score + reasons, user decision, response time, rubber-stamp flag, edit distance, feedback text, verification result, model confidence, check-in initiator, participant/run/task study metadata, and autonomy mode.

## CLI Commands

All commands use the `sc` prefix. Core surface:

```
sc run --task "..."              # main orchestration loop
sc ask "..."                     # chat without changes
sc init                          # initialize repo config
sc doctor                        # verify AWS/Bedrock setup
sc report                        # session summary

sc rules import <file>           # import constraints from AGENTS.md/CLAUDE.md
sc rules constraints             # list/add hard constraints
sc rules guidelines              # list/add behavioral guidelines
sc rules guidelines-suggest      # suggest guidelines from trace patterns

sc observe traces                # query decision history
sc observe explain <id>          # explain a specific trace
sc observe preferences           # show learned autonomy preferences
sc observe preferences-clear     # reset learned preferences
sc observe checkin-stats         # check-in usefulness metrics
sc observe leases                # list active trust grants
sc observe export                # export latest session bundle for lab analysis
sc observe reset-study-state     # clear mutable state between participants

sc config set-mode               # set qualitative autonomy mode
sc config set-verification-cmd   # custom post-write verification
```

## Configuration (SAConfig)

| Field | Default | Purpose |
|-------|---------|---------|
| `model_id` | (required) | Bedrock model ID |
| `aws_region` | us-east-1 | AWS region |
| `max_tokens` | 2500 | Model output limit |
| `temperature` | 0.0 | Model temperature |
| `lease_ttl_hours` | 72 | Lease expiration |
| `scope_budget_files` | 12 | Max files per action |
| `autonomy_mode` | balanced | User-facing autonomy preset |
| `permanent_approval_threshold` | 3 | Consecutive approvals for permanent lease |
| `read_max_chars` | 12000 | File content truncation |
| `adaptive_policy_enabled` | true | Enable heuristic policy |
| `policy_proceed_threshold` | 0.9 | Internal auto-approve threshold |
| `policy_flag_threshold` | 0.2 | Internal flag-for-review threshold |
| `strict_plan_gate` | false | Always require plan approval |
| `plan_checkpoint_max_files` | 1 | Files before plan gate fires |
| `max_plan_revisions` | 2 | Revision rounds before forcing approval |
| `verification_enabled` | true | Run post-write checks |
| `verification_timeout_sec` | 20 | Verification command timeout |
| `verification_command` | null | Custom verification command |

## Project Structure

```
dynamic_autonomy_mvp/
├── sc/
│   ├── cli.py                  # command registration and routing
│   ├── cli_shared.py           # shared CLI helpers (config, file context, truncation)
│   ├── config.py               # SAConfig dataclass with JSON persistence
│   ├── autonomy.py             # AutonomyPreferences, threshold adaptation, model payload parsing
│   ├── agent_client.py         # Bedrock client wrapper, structured JSON protocol
│   ├── policy.py               # heuristic policy scoring engine
│   ├── plan_gate.py            # plan checkpoint decision logic
│   ├── prompt_builder.py       # dynamic system prompt from trust state
│   ├── trust_db.py             # SQLite schema + all data access
│   ├── constraints.py          # AGENTS.md/CLAUDE.md rule parser
│   ├── features.py             # change pattern classification, security detection, blast radius
│   ├── schema.py               # Pydantic models (ReadRequest, IntentDeclaration, CheckInMessage)
│   ├── session.py              # message history with pinned first message
│   ├── session_feedback.py     # recent decision/correction context for prompts
│   ├── checkin_quality.py      # check-in message validation (markers, length, options)
│   ├── verification.py         # post-write verification runner
│   ├── phase.py                # workflow phase gates (research/planning/implementation/review)
│   ├── patch.py                # patch validation (path escape, scope enforcement)
│   ├── repo.py                 # git repo root resolution
│   ├── commands/
│   │   ├── admin.py            # init, doctor, ask, constraints, guidelines, import-rules
│   │   ├── observe.py          # traces, explain, preferences, checkin-stats, leases
│   │   └── shared.py           # repo/db resolution helpers
│   └── run/
│       ├── command.py          # top-level run orchestration
│       ├── read_stage.py       # read permission/policy flow
│       ├── apply_stage.py      # write policy + atomic apply + verification
│       ├── model.py            # model check-ins, phase transitions, retries
│       ├── helpers.py          # feedback learning, change metrics, policy decisions
│       ├── traces.py           # trace persistence helpers
│       ├── reporting.py        # end-of-run summary + guideline suggestions
│       └── ui.py               # terminal prompts and rendering
├── tests/                      # 58 unit tests across 18 test files
├── SPEC.md
└── README.md
```

---

# Part 2: Research

## Why This Matters

Current tools offer binary autonomy: ask before every edit, or edit automatically. Static config files (CLAUDE.md, .cursorrules) capture preferences the developer can articulate in advance, but most preferences are implicit — they show up as correction patterns, review timing, edit distance, and phase-of-work context.

Anthropic's study of millions of agent interactions (McCain et al., Feb 2026) found that agents are far more capable than their deployment patterns suggest. METR estimates Claude handles ~5-hour tasks, but real-world turn duration caps around 42 minutes. The gap isn't capability, it's trust infrastructure. Experienced developers shift from per-action approval to monitoring + targeted intervention (auto-approve rises from 20% to 40%+), and agent-initiated stops are more common than human interruptions on complex tasks. The top reason Claude self-stops is to present approach choices (35%). AdaptiveAuth learns and accelerates this behavioral shift per-developer.

## The Trace-Prompt Feedback Loop

This is the core mechanism. Every developer interaction produces a trace. Traces accumulate into trust scores, correction patterns, and behavioral guidelines. These are queried at session start to build the system prompt the model receives. The model then uses that context to reason about when to check in.

Concretely: the developer corrects the agent's error handling in session 3. That correction is logged as a trace with `change_pattern = "error_handling"`, `user_decision = "approve"`, `user_feedback_text = "Use AppError with error codes"`. In session 4, the prompt builder does two things:

1. **Trust summary**: the model sees "Low-trust areas: error_handling — the developer has corrected you here before." Vague on purpose — no numeric scores, just enough for the model to reason about its own uncertainty.
2. **Recent corrections**: the model sees the developer's own words. Specific and actionable.

After 3+ corrections on the same pattern, the system suggests a behavioral guideline. Once accepted, the model follows the directive instead of checking in. Correction overhead drops to zero for that pattern.

Full cycle: **traces → trust scores → prompt context → model reasoning → check-in decisions → developer response → traces**.

## Pair Mode UX (implemented)

```
$ sc run --task "Refactor payment validation to use new schema"

[AdaptiveAuth] Loaded trust profile: 847 prior interactions
[AdaptiveAuth] Session started. Agent working...

── Agent Plan ──────────────────────────────────────────────────
Subtasks:
  1. Update PaymentValidator.validate()     → CHECK-IN (corrected similar 3x)
  2. Update test_payment_validation.py      → AUTO (12 approvals, 0 corrections)
  3. Update PaymentTypes API interface      → FLAG (shared interface, 3 dependents)
  4. Update API docs                        → AUTO (high trust)
────────────────────────────────────────────────────────────────

[1/4] PaymentValidator.validate()
  Checking in because: you've corrected my payment validation changes 3 times.
  [diff preview]
  (a)pprove  (e)dit  (d)eny  (s)kip  > a

[2/4] test_payment_validation.py — auto-approved (12 prior approvals)
[3/4] PaymentTypes API interface — completed, flagged for summary review
[4/4] API docs — auto-approved

── Session Summary ─────────────────────────────────────────────
  2 auto-approved  |  1 check-in (approved)  |  1 flagged
────────────────────────────────────────────────────────────────
```

## Phase-Aware Behavior

| Phase | Default | Learns to... |
|---|---|---|
| Research | Read freely, write findings to markdown | Which modules need deep vs. shallow reads |
| Planning | Heavy check-ins, developer annotates iteratively | What the developer always overrides in plans |
| Implementation | Minimal interruptions, execute approved plan | Which implementation patterns get corrected |
| Review | Surface results, flag failures | Which test failures are blocking vs. ignorable |

## System Prompt

Built dynamically per-session from the trust DB. The model is an active participant in oversight but doesn't get information it could exploit — no exact trust scores (could game thresholds), no list of which files will be auto-approved (prevents strategic behavior). It does know which areas it's been corrected on and what the hard constraints are.

The prompt includes: role framing, check-in guidance, trust summary (high/low trust areas by name, no scores), hard constraints, behavioral guidelines, last 5 corrections with developer feedback text, autonomy preferences, phase-specific guidance, session warnings.

## Evaluation

### Metrics

**Primary:** correct trust rate, correct caution rate, unnecessary interruption rate, missed check-in rate.

**Two-sided calibration:** CLI-initiated useful/wasted, model-initiated useful/wasted, user interrupt rate, model-CLI agreement rate.

**Secondary:** check-in frequency over time, task completion time, user correction rate, trust score trajectory.

**Guideline loop:** adoption rate, correction rate pre/post guideline, pattern coverage.

**Approval quality:** rubber-stamp rate (<5s), batch vs. realtime accuracy, false confidence rate.

**Preference learning:** correction repeat rate across sessions, cold-start corrections to stable behavior.

### Baselines

1. Always Ask — 100% correct caution, 0% correct trust, maximum interruption
2. Never Ask — 0% correct caution, maximum missed check-ins
3. Static Rules — hand-coded from survey data, explicit preferences only
4. Heuristic — the weighted policy (current implementation)
5. Bandit — the learned policy (future)

The gap between static rules and the learned policy is the paper's core finding: implicit preferences that config files can't capture.

### Protocol (adapted from PAHF)

Phase 1 (sessions 1-5): cold start, sensible defaults, measure corrections to stable behavior.
Phase 2 (sessions 6-15): evaluate learned preferences, compare all baselines.
Phase 3 (sessions 16-20): preference shift (developer changes style/framework). Measure adaptation speed.
Phase 4 (sessions 21-25): evaluate post-shift adaptation. Should be faster than the original cold start.

Per-trace: extract features, run each policy, compare against ground truth, compute quality-weighted reward.

Reporting: accuracy/precision/recall per policy, learning curves, feature ablation, qualitative examples of implicit preference capture, survey alignment, approval quality distributions, preference learning curves, initiator distribution over time, model calibration, CLI calibration, three-way agreement (CLI x model x user), model confidence correlation with outcomes.

## Related Work

**CowCorpus (Huq et al., 2025, arXiv 2602.17588).** 400 real-user web navigation trajectories. Four interaction styles (hands-off, hands-on, collaborative, takeover) stable per user across tasks. Style-conditioned models improved intervention prediction 61-63%. Validates our bet that per-developer preferences are learnable. They retrain the model; we learn a separable governance policy that works with any model.

**Grunde-McLaughlin et al. (2025, arXiv 2602.16844).** Three user studies on Computer Use Agents. The best trace interface helped developers find errors faster (Hedges' g: -0.65) but increased false confidence when wrong (g: 0.85). Developers rubber-stamp because the process *looks* reasonable. We took: review duration tracking as a quality signal, assumptions field in check-ins, asymmetric quality weighting (negative signals always full weight, positive signals discounted by review speed).

**PAHF (Liang et al., 2026, arXiv 2602.16173).** Meta/Princeton framework for continual personalization. Post-action feedback is "particularly important for robust personalization without pre-existing user data" — our cold-start scenario exactly. We took: immediate correction injection, drift detection design, four-phase evaluation protocol. Key difference: PAHF's memory is model-internal; ours is CLI-governed.

## Future Work

### Near-term (post lab study)

1. **Learned policy weights** — replace guessed heuristic weights with a classifier trained on `decision_traces` data. Contextual bandit (LinUCB) over check-in decisions. Asymmetric reward: missing a needed check-in costs more than an unnecessary interruption.

2. **Async delegation mode** — background execution with `sc status`, `sc review`, check-in queue, session summaries.

3. **Structured plan rendering** — render plans as structured markdown with section headers, file-level summaries, and inline code samples. Goal: minimize ambiguity before the developer approves a plan.

4. **Deterministic guideline enforcement** — currently behavioral guidelines are purely soft (injected into the system prompt as preferred style). The model can ignore them. When a guideline is accepted, classify it into one of three enforcement tiers:
   - **Path constraint** (e.g., "never modify production configs") → convert to hard constraint in `hard_constraints` table (deterministic, CLI-enforced).
   - **Content rule** (e.g., "use AppError, not generic Error") → generate a grep/lint check added to the post-write verification pipeline (deterministic, fails apply stage).
   - **Style preference** (e.g., "prefer composition over inheritance") → keep as prompt injection (soft, model-dependent).
   The model can do this classification at guideline creation time. This closes the gap between "the system knows what the developer wants" and "the system actually enforces it."

5. **Spec-aware execution loop** — optional `--spec` artifacts should eventually support structured parsing instead of simple bounded prompt injection. The current implementation injects a truncated spec digest into the system prompt and requires the plan to expose `requirements_covered`, `expected_change_types`, and `potential_deviations`. Future work is retrieving exact requirement sections on demand and storing spec lineage more explicitly for analysis.

### Lab study shipping requirements

These items are required before distributing the prototype to study participants.

1. **Qualitative autonomy control** — expose `strict` / `balanced` / `milestone` / `autonomous` as the primary control surface. Threshold tuning remains internal and optionally available only for research/debug workflows.

2. **Milestone-first check-ins** — default behavior should align with survey feedback:
   - plan approval
   - phase transitions
   - first risky write batch
   - architectural or interface tradeoffs
   - verification failures / recovery proposals
   Routine low-risk edits should not interrupt.

3. **Study metadata on every trace** — record enough context to analyze behavior offline:
   - participant identifier
   - study run identifier
   - optional task identifier
   - autonomy mode used for the run

4. **Operator-grade export** — one command should export session traces, report summary, active preferences, constraints, and guidelines for a participant/run without manual SQLite queries.

5. **Operator-grade reset** — one command should reset learned state for a clean participant start:
   - leases
   - traces
   - approval history
   - learned autonomy preferences
   Rules imported from fixture files can then be re-imported deterministically.

6. **Qualitative reason strings** — the runtime UI should explain decisions in natural language:
   - why a read/write/check-in happened
   - why autonomy increased or decreased
   - what milestone or risk condition triggered the pause
   Users should not need to understand the scoring model to supervise the agent.

### Medium-term

6. **Interaction-style cold start prior (CowCorpus)** — classify users as hands-off/hands-on/collaborative/takeover from first 3-5 sessions using interrupt frequency, review duration, edit distance. Use style as a prior for thresholds before enough traces accumulate.

7. **Reversibility as first-class risk signal (McCain)** — add `is_reversible` to traces. Score irreversible actions with an explicit penalty separate from blast radius.

8. **Interrupt taxonomy (McCain)** — extend user_response with `partial_approve`, `user_takeover`. Add `interrupt_reason`: correction/takeover/redirect/excessive_execution/sufficient_progress. Takeover/sufficient-progress interrupts should be neutral or positive, not denials.

9. **Review-phase failure preference learning** — track developer treatment of failing checks (blocking vs. ignorable). Persist in traces and surface in trust/prompt context.

10. **Research-phase markdown writeback** — controlled write policy for `.md` findings/plan artifacts during research. Keep non-markdown writes blocked.

### Long-term

11. **Full RL** — only if the bandit can't capture sequential dependencies within sessions. Episode = session, state = context + session history, PPO or DQN.

12. **Trust decay** — exponential decay on trust scores (target: ~14-day half-life). Not yet implemented because we need real usage data to validate the decay rate.

13. **Drift detection** — track corrections that contradict existing guidelines. If 2+ contradictions, flag at session end for review.

## Todo Backlog (Policy Enforcement Refactor)

These items are approved for the next spec iteration and should be treated as implementation todos.

1. **Verifiability-first policy taxonomy** — classify every policy by enforcement capability, not by domain:
   - `deterministic_enforced` (hard block/fail)
   - `deterministic_advisory` (warn + explicit override)
   - `best_effort` (prompt steering only)
   This replaces the implicit “file-access => hard constraint, everything else => guideline” split.

2. **Policy expectation disclosure at creation time** — when a user adds/imports a rule, immediately report:
   - enforcement class (`deterministic_enforced` / `deterministic_advisory` / `best_effort`)
   - exact matched scope (files/globs)
   - failure behavior (block / prompt / note)
   - rationale if downgraded to best-effort.

3. **Vague-scope resolution step** — for ambiguous policies (e.g., “frontend style files”), require disambiguation before persisting:
   - propose concrete candidate scopes
   - require user confirmation
   - store normalized scope set + original natural-language policy text.

4. **Promotable policy pipeline** — automatically attempt to promote verifiable natural-language policies to deterministic enforcement:
   - process rules (e.g., “always run tests”) -> verification hooks
   - content rules (e.g., “use AppError, not Error”) -> static checks/lints
   - access rules -> hard constraints
   - non-verifiable policies remain best-effort guidelines.

5. **LLM policy judge/compiler** — add a dedicated policy-compiler model call that decides:
   - prompt-only guidance vs deterministic script/check
   - confidence + explanation for classification
   - generated checker spec (not raw shell by default), with CLI validation before activation.
   Runtime enforcement remains CLI-deterministic; the LLM is only a compiler/planner.

6. **Subagent execution architecture (experimental)** — evaluate a two-agent topology:
   - `planner/oversight subagent`: plans work according to autonomy and policy rules, emits checkpoints/delegations
   - `coding subagent`: produces edits within delegated scope
   - CLI remains the single enforcement boundary across both agents.
   This is research-track; do not put on critical lab path until deterministic traceability is validated.

## Design Decisions

| Decision | Current | Revisit if... |
|---|---|---|
| Learning algorithm | Heuristic weights | Lab study data available → contextual bandit |
| Change pattern classification | Rule-based (features.py) | Rules miss too many patterns → lightweight LLM |
| Trust decay | None implemented | Users report stale trust → add exponential decay |
| Lease threshold | 3 consecutive approvals | Too aggressive or conservative |
| Model trust visibility | Vague summary, no scores | Model needs more to reason well, or is gaming it |
| Initiator weighting | Equal CLI vs. model | Data shows one source is consistently better |
| Model confidence | Logged, not trusted | Correlates well with outcomes → make it active |
| Cold start | Sensible defaults, no interview | Takes too many interactions → add light interview |
| Guideline threshold | 3 corrections on same pattern | Too noisy or too conservative |
| Guideline authorship | CLI drafts, developer confirms | Consistently accepted → reduce friction |
| Model writes own rules | Never | N/A — hard architectural constraint |
| Rubber-stamp threshold | <5s review duration | 5s too aggressive → adjust per task complexity |
| Approval quality discount | 0.5x rubber-stamp | Starves learning or corrupts trust |
| Preference learning | Model-based (no regex) | Model calls too slow → add fast-path heuristics |
| Preference accumulation | OR/UNION, no decay | Preferences go stale → add decay mechanism |
