# AdaptiveAuth

## What this is

## Implementation status (current prototype)

Legend: [implemented], [partial], [not implemented]

- [implemented] Core governance loop (`sc run`/`sc start`) with untrusted-model enforcement.
- [implemented] Two-sided check-ins (CLI policy + model-proactive) with `check_in_initiator` tracing.
- [implemented] Dynamic prompt context from trust summary, constraints, guidelines, and recent feedback.
- [implemented] Plan checkpoint gate with revise/deny loop and persisted plan revision events.
- [implemented] Heuristic adaptive policy with review-duration/rubber-stamp quality weighting.
- [implemented] End-of-run summary + guideline suggestion flow + observability (`traces`, `explain`, `report`).
- [implemented] Rule import (`import-rules` / `import`) into hard constraints + behavioral guidelines.
- [partial] Pair mode implemented; async mode flag exists but runtime supports pair only.
- [partial] Data model partially matches this spec; implementation uses `decision_traces`-centric schema.
- [partial] Agent protocol is structured JSON but simpler than full target protocol in this document.
- [not implemented] Training/inference (`policy train/eval`) not implemented yet.
- [not implemented] Full async delegation queue (`status`/`review`) not implemented yet.
- [not implemented] Full drift detection/takeover detection loops not implemented yet.
- [not implemented] Interaction-style cold-start prior (CowCorpus archetypes) not yet operationalized.
- [not implemented] Reversibility (`is_reversible`) is not yet a first-class policy feature.
- [not implemented] Positive handoff interrupts vs corrective interrupts are not yet separated in runtime scoring.
- [not implemented] Research-phase markdown writebacks (notes/findings) are not currently allowed by phase gate.
- [not implemented] Review-phase learning of blocking vs ignorable failures is not explicitly modeled yet.

### Explicit gaps tracked for next iteration (not implemented)

1. **Interaction-style cold start prior (CowCorpus paper)**
   - Add a `user_profile` (or `sessions.interaction_style`) field:
     - `hands_off` | `hands_on` | `collaborative` | `takeover`
   - Classify early using first 3-5 sessions from:
     - interrupt frequency
     - review duration
     - edit distance / correction rate
   - Use style as a prior for heuristic thresholds before enough traces accumulate.

2. **Reversibility as first-class risk signal (McCain)**
   - Add `is_reversible` to ActionContext + traces.
   - Score irreversible actions with an explicit penalty separate from blast radius.
   - Keep reversibility orthogonal to code-diff size and dependency impact.

3. **Interrupt taxonomy in outcomes (McCain)**
   - Extend `user_response` with:
     - `partial_approve`
     - `user_takeover`
   - Add `interrupt_reason`:
     - `correction` | `takeover` | `redirect` | `excessive_execution` | `sufficient_progress`
   - Update trust scoring so takeover/sufficient-progress interrupts are neutral or positive, not denials.

4. **Research-phase markdown findings writeback**
   - Current gate blocks all writes during research.
   - Add controlled write policy for `.md` findings/plan artifacts in research.
   - Keep non-markdown writes blocked.

5. **Review-phase failure preference learning**
   - Track developer treatment of failing checks (`blocking` vs `ignorable`).
   - Persist this signal in traces and surface it in trust/prompt context.
   - Use it in policy decisions during review/test stages.

6. **Structured plan rendering with code previews (survey feedback)**
   - Render plans as structured markdown with section headers, file-level summaries, and inline code samples showing what will change.
   - Display via Rich markdown rendering in the terminal so large plans are scannable.
   - Goal: by the time the developer approves a plan, there is minimal ambiguity about what the agent will produce.
   - Requires extending `IntentDeclaration` or adding a plan preview stage between intent and generation.

## Project Overview

A CLI governance layer between a developer and an LLM coding agent. It learns when to pause and ask the developer vs. when to proceed autonomously, adapting over time to each developer's implicit preferences.

The model is untrusted. It proposes actions; the CLI enforces all reads, writes, and check-ins. Trust is built from interaction traces — approval history, correction patterns, review timing — not from the model's self-assessment. The model participates in oversight by reasoning about its own uncertainty and surfacing architectural decisions, but the CLI makes the final call.

This targets skilled engineers who plan, supervise, and validate. Not really as a vibe-coding tool. The goal: supervision gets more efficient over time because the system learns what this particular developer actually cares about.

## Why this matters

Current tools offer binary autonomy: ask before every edit, or edit automatically. Static config files (CLAUDE.md, .cursorrules) capture preferences the developer can articulate in advance, but most preferences are implicit — they show up as correction patterns, review timing, edit distance, and phase-of-work context. Nobody writes "check in on error handling but not test generation" in a config file, but that preference is clearly visible in interaction traces.

Anthropic's study of millions of agent interactions (McCain et al., Feb 2026) found that agents are far more capable than their deployment patterns suggest. METR estimates Claude handles ~5-hour tasks, but real-world turn duration caps around 42 minutes. The gap isn't capability, it's trust infrastructure. Experienced developers shift from per-action approval to monitoring + targeted intervention (auto-approve rises from 20% to 40%+), and agent-initiated stops are more common than human interruptions on complex tasks. The top reason Claude self-stops is to present approach choices (35%). AdaptiveAuth learns and accelerates this behavioral shift per-developer.


## User experience

### Pair mode (implemented)

Interactive. Agent proposes, developer reviews in real-time.

```
$ aa start --mode pair --task "Refactor payment validation to use new schema"

[AdaptiveAuth] Loaded trust profile: 847 prior interactions
[AdaptiveAuth] Imported 3 rules from CLAUDE.md
[AdaptiveAuth] Session started. Agent working...

── Agent Plan ──────────────────────────────────────────────────
Subtasks:
  1. Update PaymentValidator.validate()     → CHECK-IN (corrected similar 3x)
  2. Update test_payment_validation.py      → AUTO (12 approvals, 0 corrections)
  3. Update PaymentTypes API interface      → FLAG (shared interface, 3 dependents)
  4. Update API docs                        → AUTO (high trust)
────────────────────────────────────────────────────────────────

[1/4] PaymentValidator.validate()
  Restructuring validate() to use SchemaV2.
  Preserving existing edge case handler for expired cards.

  Checking in because: you've corrected my payment validation
  changes 3 times in the last 2 weeks.

  [diff preview]

  (a)pprove  (e)dit  (d)eny  (s)kip  > a

[2/4] test_payment_validation.py — auto-approved (12 prior approvals)
[3/4] PaymentTypes API interface — completed, flagged for summary review
[4/4] API docs — auto-approved

── Session Summary ─────────────────────────────────────────────
  2 auto-approved  |  1 check-in (approved)  |  1 flagged
  Flagged: PaymentTypes interface change affects 3 downstream consumers.
  View full diff? (y/n) >
────────────────────────────────────────────────────────────────
```

### Async mode (not implemented yet)

Developer hands off a task, checks back later.

```
$ aa start --mode async --task "Add cursor-based pagination to all list endpoints"

[AdaptiveAuth] Agent working in background...

$ aa status

── Task Progress ───────────────────────────────────────────────
  4/7 subtasks complete, 1 awaiting input, 2 remaining

  ✓ users/list.py          — auto-approved, tests pass
  ✓ projects/list.py       — auto-approved, tests pass
  ✓ tasks/list.py          — auto-approved, tests pass
  ✓ shared/pagination.py   — auto-approved (utility, high trust)

  ⏸ billing/list.py        — AWAITING INPUT
    "This endpoint has custom rate limiting that interacts with
     pagination. Two approaches:
     (A) Paginate first, then rate-limit per page
     (B) Rate-limit globally, paginate within the limit
     Checking in because you've corrected my billing changes before."

    (a) Approach A  (b) Approach B  (v)iew diff for each  >

  ○ notifications/list.py  — queued
  ○ Integration tests       — queued

  Time elapsed: 23 min | Est. remaining: 8 min
────────────────────────────────────────────────────────────────
```

### Phase-aware behavior

| Phase | Default | Learns to... |
|---|---|---|
| Research | Read freely, write findings to markdown | Which modules need deep vs. shallow reads |
| Planning | Heavy check-ins, developer annotates iteratively | What the developer always overrides in plans |
| Implementation | Minimal interruptions, execute approved plan | Which implementation patterns get corrected |
| Review | Surface results, flag failures | Which test failures are blocking vs. ignorable |


## Architecture

Check-ins come from two independent sources:

1. **CLI policy engine** — evaluates trust scores, file features, constraints, session state. Decides auto-approve vs. check-in vs. deny. Runs regardless of what the model does.
2. **Model system prompt** — the model is told its trust context and instructed to reason about uncertainty. It pauses for architectural decisions, approach tradeoffs, plan deviations. Does not pause for file permissions or routine implementation.

Either side can trigger a check-in independently. Both are logged with `check_in_initiator` so we can learn which source is better calibrated over time.

This visual was generated by Claude Opus 4.6:

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
│  │   agents.md / CLAUDE.md parser               │   │
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

### The trace → prompt feedback loop

This is the core mechanism. Every developer interaction produces a trace. Traces accumulate into trust scores, correction patterns, and behavioral guidelines. These are queried at session start (and at phase transitions) to build the system prompt the model receives. The model then uses that context to reason about when to check in. This is a hueristic guess until we run user-studies or get survey results to learn implicit/explicit preferences.

Concretely: the developer corrects the agent's error handling in session 3. That correction is logged as a trace with `change_pattern = "error_handling"`, `user_response = "approve_with_edits"`, `user_feedback = "Use AppError with error codes"`. The trust score for error_handling drops. In session 4, when the prompt builder runs, it does two things:

1. **Trust summary** (from `trust_scores` table): the model sees "Low-trust areas: error_handling patterns — the developer has corrected you here before." This is vague on purpose to avoid hacking, no numeric scores, just enough for the model to reason about its own uncertainty.
2. **Recent corrections** (from `traces` table, last 5 corrections): the model sees "error_handling in src/api/handler.py — Developer said: Use AppError with error codes." This is specific and actionable.

The model now has two signals pushing it toward caution on error handling: a vague trust warning and a concrete correction with the developer's own words. When it encounters an error handling decision in session 4, it's more likely to proactively check in — not because the CLI forced it, but because the prompt gave it reasons to be uncertain.

Meanwhile, the CLI policy engine independently sees the lower trust score for error_handling and may force a check-in anyway. Both sides arrive at the same conclusion through different paths. The traces log which side triggered the check-in (`check_in_initiator`), so over time we learn whether the model's self-assessment or the CLI's score-based policy is better calibrated for this developer.

After 3+ corrections on the same pattern, the system suggests a behavioral guideline. If the developer accepts "Use AppError with error codes, not generic Error", that guideline goes into the prompt as a standing instruction — not just a trust warning, but a directive. The model stops checking in on error handling (trust rebuilds from approvals) and instead just follows the guideline. The developer's correction overhead drops to zero for that pattern.

This is the full cycle: **traces → trust scores → prompt context → model reasoning → check-in decisions → developer response → traces**. The model doesn't learn through ML-techniques, it receives progressively better context each session and reasons over it. The actual learning happens in the trust DB and the guideline table, outside the model.


## Data model (SQLite) — target schema (partially implemented)

```sql
CREATE TABLE hard_constraints (
    id INTEGER PRIMARY KEY,
    path_pattern TEXT NOT NULL,          -- glob, e.g. "src/auth/*"
    constraint_type TEXT NOT NULL,       -- "always_check_in" | "always_deny" | "always_allow"
    source TEXT NOT NULL,                -- "agents_md" | "user_explicit" | "system"
    overridable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trust_scores (
    id INTEGER PRIMARY KEY,
    file_path TEXT NOT NULL,
    action_type TEXT NOT NULL,           -- "read" | "write" | "create" | "delete" | "refactor"
    change_pattern TEXT,                 -- "test_generation" | "error_handling" | "api_change" etc.
    approval_count INTEGER DEFAULT 0,
    denial_count INTEGER DEFAULT 0,
    correction_count INTEGER DEFAULT 0,
    avg_edit_distance REAL DEFAULT 0.0,
    avg_review_time_ms REAL DEFAULT 0.0,
    last_interaction TIMESTAMP,
    trust_score REAL DEFAULT 0.0,
    UNIQUE(file_path, action_type, change_pattern)
);

CREATE TABLE leases (
    id INTEGER PRIMARY KEY,
    file_path TEXT NOT NULL,
    action_type TEXT NOT NULL,
    lease_type TEXT NOT NULL,            -- "permanent" | "session" | "timed"
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    grant_reason TEXT,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_reason TEXT
);

CREATE TABLE traces (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Context (policy inputs)
    file_path TEXT NOT NULL,
    action_type TEXT NOT NULL,
    change_pattern TEXT,
    workflow_phase TEXT,
    diff_size INTEGER,
    blast_radius INTEGER,
    is_reversible BOOLEAN,              -- [not implemented] reversible vs irreversible action
    is_security_sensitive BOOLEAN,
    is_shared_interface BOOLEAN,
    code_complexity_score REAL,
    file_author TEXT,

    -- Trust history at decision time
    prior_approvals INTEGER,
    prior_denials INTEGER,
    prior_corrections INTEGER,
    current_trust_score REAL,
    has_active_lease BOOLEAN,

    -- Session state
    session_action_count INTEGER,
    session_recent_denials INTEGER,
    session_recent_corrections INTEGER,
    time_since_last_interaction_ms INTEGER,

    -- Policy decision
    policy_decision TEXT NOT NULL,       -- "check_in" | "auto_approve" | "auto_approve_flag" | "deny"
    policy_confidence REAL,

    -- Two-sided check-in tracking
    check_in_initiator TEXT,            -- "cli_policy" | "model_proactive" | "user_interrupt" | "none"
    model_stated_reason TEXT,
    model_confidence_self_report REAL,

    -- Outcome
    user_response TEXT,                 -- "approve" | "deny" | "approve_with_edits" | "not_reviewed"
                                        -- [planned/not implemented] add "partial_approve" | "user_takeover"
    interrupt_reason TEXT,              -- [not implemented] correction/takeover/redirect/excessive_execution/sufficient_progress
    user_edit_distance INTEGER,
    user_response_time_ms INTEGER,
    review_duration_seconds REAL,       -- wall-clock time from presentation to response
    review_mode TEXT,                   -- "realtime" | "batch"
    user_reverted BOOLEAN DEFAULT FALSE,
    user_feedback TEXT,                 -- developer's correction explanation, injected into next prompt
    tests_passed_after BOOLEAN,
    user_corrected_despite_tests BOOLEAN,
    test_coverage_of_changed REAL,

    was_correct_decision BOOLEAN        -- computed post-hoc for evaluation
);

CREATE TABLE behavioral_guidelines (
    id INTEGER PRIMARY KEY,
    guideline TEXT NOT NULL,
    source TEXT NOT NULL,                -- "imported" | "learned" | "user_explicit"
    source_file TEXT,
    change_pattern TEXT,
    confidence REAL DEFAULT 1.0,
    correction_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

-- No preference_hints table for now. Recent corrections are queried
-- directly from traces and injected into the session prompt.
-- Add a dedicated table if simple injection gets too noisy.

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,                 -- "pair" | "async"
    interaction_style TEXT,             -- [not implemented] "hands_off" | "hands_on" | "collaborative" | "takeover"
    task_description TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_actions INTEGER DEFAULT 0,
    total_check_ins INTEGER DEFAULT 0,
    total_auto_approvals INTEGER DEFAULT 0,
    total_corrections INTEGER DEFAULT 0,
    total_denials INTEGER DEFAULT 0,
    session_takeover BOOLEAN DEFAULT FALSE,
    model_version TEXT
);
```

Agents.md/CLAUDE.md files are parsed into `hard_constraints`. Conservative: if a rule can't be confidently parsed, it becomes `always_check_in` rather than a guess. Soft hints like "be careful with billing" lower initial trust for matching paths instead of creating hard constraints.


## Policy engine

### Heuristic baseline (implemented)

Four possible decisions: CHECK_IN, AUTO_APPROVE, AUTO_APPROVE_FLAG, DENY.

Decision inputs (the "ActionContext"): file path, action type, change pattern, workflow phase, diff size, blast radius, security sensitivity, shared interface flag, code complexity, prior approvals/denials/corrections, edit distance, trust score, active leases, session denials, session corrections, time since last check-in, action count.

Evaluation order:

1. Hard constraints win. `always_deny` / `always_check_in` / `always_allow` are immediate returns.
2. Active leases grant auto-approval, unless there's been a denial this session.
3. Score computation from features:
   - History (strongest): approvals +0.3, denials −0.8, corrections −0.5, edit distance −0.4
   - Risk: security-sensitive −3.0, shared interface −2.0, blast radius −0.5 to −1.5, large diffs −0.5 to −1.0
   - Phase: planning −2.0 (always ask more), research +1.0 (reads are cheap)
   - Session momentum: recent denial −2.0, many corrections −1.0
4. Thresholds: ≥ 3.0 → AUTO_APPROVE. ≥ 0.0 → AUTO_APPROVE_FLAG. < 0.0 → CHECK_IN.

All weights are initial guesses that Kevin and I have determined as importance, surveys will tune this data.

### Contextual bandit (future, not implemented)

After 50-100+ traces, train a learned policy. Contextual bandit over check-in decisions. State = vectorized ActionContext. Actions = {CHECK_IN, AUTO_APPROVE, AUTO_APPROVE_FLAG}. 

Reward table (asymmetric — missing a needed check-in costs more than an unnecessary interruption):

| Decision | Outcome | Reward |
|---|---|---|
| AUTO_APPROVE | Would have been approved | +1.0 |
| AUTO_APPROVE | Denied or heavily edited | −1.0 |
| AUTO_APPROVE | Minor edits | −0.3 |
| CHECK_IN | Developer had meaningful input | +1.0 |
| CHECK_IN | Developer considered then approved | +0.3 |
| CHECK_IN | Rubber-stamped instantly | −0.5 |
| AUTO_APPROVE_FLAG | Reviewed | +0.5 |
| AUTO_APPROVE_FLAG | Denied or heavily edited | −0.5 |

Approval quality weighting: not all approvals are equal. Positive rewards are discounted by review quality — rubber-stamps (< 5s review) get 0.5x, batch reviews get 0.7x. Negative signals (denials, heavy corrections) are never discounted. Grunde-McLaughlin et al. showed better oversight interfaces increase false confidence; approval speed is the correction signal.

### Full RL (if needed, not implemented)

Will delegate this decision to Kevin, Leijie, Amy.

Only if the bandit can't capture sequential dependencies (e.g., trust building within a session). Episode = session, state = context + session history, PPO or DQN. Don't build until bandit results show it's needed.


## CLI commands (target UX; current implementation uses `sc` command set)

```
aa start [--mode pair|async] [--task "..."]
aa status                               # async progress
aa review                               # flagged items + async queue
aa history [--file path] [--session id] [--last n]
aa trust [path]
aa trust set <path> <level>             # always_ask | cautious | trusted | auto
aa trust revoke <path>
aa policy eval [--traces path] [--baseline heuristic|bandit]
aa policy train [--traces path] [--algorithm linucb|epsilon_greedy]
aa import [CLAUDE.md | .cursorrules | AGENTS.md]
aa export
aa explain <trace_id>
aa guidelines [--active] [--learned] [--imported]
aa guidelines add "<text>" [--pattern <pattern>]
aa guidelines remove <id>
```


## Session flow

Initialize: create session, load trust DB + constraints + policy, build system prompt with trust context, start agent with task + prompt.

Main loop per action:

1. If the agent voluntarily pauses (CheckInMessage) → route to developer, log with initiator="model_proactive", feed response back. Model confidence is logged but not acted on.
2. For file actions → build ActionContext, run policy against constraints.
3. Execute: DENY notifies agent. AUTO_APPROVE validates (hash check etc.) then applies. AUTO_APPROVE_FLAG applies + flags for summary. CHECK_IN presents to developer, records wall-clock review duration and tags realtime vs. batch.
4. Log full trace. Update session state. Rebuild prompt on phase transitions.

Session end: print summary, update trust scores, check for guideline candidates (§10.2), present any suggestions.


## Agent protocol (partially implemented)

Structured JSON messages, validated by CLI before acting.

**ReadRequest** — files + reason. **IntentDeclaration** — phase, plan, subtasks (each with file, action type, change pattern, confidence), estimated files/blast radius. **FileUpdate** — path, original hash (for conflict detection), content, summary, subtask ref. **CheckInMessage** — reason, type (plan_review / decision_point / progress_update / deviation_notice / phase_transition / uncertainty), content, options, assumptions, confidence. **PlanRevision** — plan path, round number, developer annotations, agent changes.

The assumptions field in CheckInMessage is important: Grunde-McLaughlin et al. found that surfacing what the agent assumed (without being asked) had the highest error detection rate across all interface designs they tested.


## System prompt (implemented with current prompt-builder scope)

Built dynamically per-session from the trust DB and traces (see "trace → prompt feedback loop" above). Updated at phase transitions. The model is an active participant in oversight but doesn't get information it could exploit.

The CLI handles file-level governance. The model handles design-level reasoning. The model doesn't know exact trust scores (could game thresholds) or which files will be auto-approved (prevents strategic behavior). It does know which areas it's been corrected on and what the hard constraints are.

The prompt includes:
- Role framing: "you are the builder consulting on structural decisions, not asking permission"
- Check-in guidance: surface expensive-to-reverse decisions, not easy-to-fix ones
- Check-in structure: what + why, alternatives, tradeoffs, recommendation, assumptions, confidence
- Trust summary: high/low trust areas by name (no scores), correction patterns by type (not file)
- Hard constraints
- Behavioral guidelines from past corrections
- Last 5 corrections with developer feedback text (bridges the gap before guideline threshold)
- Phase-specific guidance (see table below)
- Session warnings (e.g., recent denials)

| Phase | Model guidance |
|---|---|
| Research | Read freely. Don't implement. Check in when ready to propose a plan. |
| Planning | Present plan before implementing. Check in on plan + approach choices. Don't code until plan is approved. |
| Implementation | Minimize check-ins. Execute the plan. Only pause for unplanned architectural decisions or significant confidence drops. |
| Review | Run tests, surface results. Check in on unexpected failures. |


## Features (partially implemented)

Per file change: diff size, files in diff, blast radius (import graph), shared interface flag, security sensitivity (path patterns + content), cyclomatic complexity, git authorship, recency of developer edits, test coverage.

Each change is classified into a semantic pattern (test_generation, error_handling, api_change, refactor, config_change, documentation, new_feature, bug_fix, dependency_update, ui_change, data_model_change, security_sensitive) so trust generalizes across files with similar change types. Rule-based classification first; upgrade to lightweight LLM classification if rules miss too many patterns.


## Trust updates (partially implemented)

After each interaction, the trust record for that (file, action_type, change_pattern) is updated:
- Approval → increment approval count
- Denial → increment denial count
- Correction (approve-with-edits) → increment correction count, update rolling average edit distance

Composite score:

    raw = (approvals × 0.3) − (denials × 0.8) − (corrections × 0.5) − (edit_distance × 0.01)
    trust = raw × exp(−0.05 × days_since_last_interaction)


Leases auto-grant after enough consecutive approvals with zero denials and ≤1 correction. Auto-revoke when denials or corrections hit a threshold.

### Corrections → guidelines

Trust scores change *how often* the system asks. Guidelines change *what the model does*. "Low trust on error handling" means more check-ins; "Use AppError with error codes" means the model actually changes its behavior.

When the system sees 3+ corrections on the same change pattern across files, it drafts a guideline suggestion. Confidence is higher when corrections span multiple files (pattern-level preference, not file-specific). At session end, candidates are presented: accept, edit, reject, or defer. Accepted guidelines go into the system prompt for all future sessions.

The model never writes its own rules. The CLI detects patterns, drafts suggestions, the developer confirms. The model receives guidelines through the prompt. This preserves the untrusted-model boundary.

Evaluation signal: if correction rates drop on a pattern after a guideline is added, the feedback loop works.

### Immediate correction feedback

The guideline threshold is 3 corrections, so the first two are invisible to the model. To bridge this gap, we query the last 5 corrections from the traces table and inject their descriptions + developer feedback into the session prompt. No separate table, no similarity matching. If this gets too noisy, add a dedicated preference_hints table with deduplication later.

### Drift detection (future, not implemented)

Once guidelines exist and have been active for multiple sessions: track corrections that contradict them. If 2+ contradictions, flag at session end. Developer can update, remove, or keep the guideline. Similarly, session takeover detection (developer making manual commits, bypassing the agent entirely) is deferred — just a manual boolean flag for now.


## Evaluation

### Metrics

Primary: correct trust rate, correct caution rate, unnecessary interruption rate, missed check-in rate.

Two-sided calibration: CLI-initiated useful/wasted, model-initiated useful/wasted, user interrupt rate, model-CLI agreement rate.

Secondary: check-in frequency over time, task completion time, user correction rate, trust score trajectory.

Guideline loop: adoption rate, correction rate pre/post guideline, pattern coverage.

Approval quality: rubber-stamp rate (< 5s), batch vs. realtime accuracy, false confidence rate.

Preference learning: correction repeat rate across sessions, cold-start corrections to stable behavior.

### Baselines

1. Always Ask — 100% correct caution, 0% correct trust, maximum interruption
2. Never Ask — 0% correct caution, maximum missed check-ins
3. Static Rules — hand-coded from survey data, explicit preferences only
4. Heuristic — the weighted policy (§5.1)
5. Bandit — the learned policy (§5.2)

The gap between static rules and the learned policy is the paper's core finding: implicit preferences that config files can't capture.

### Protocol (adapted from PAHF)

Phase 1 (sessions 1–5): cold start, sensible defaults, measure corrections to stable behavior.
Phase 2 (sessions 6–15): evaluate learned preferences, compare all baselines.
Phase 3 (sessions 16–20): preference shift (developer changes style/framework). Measure adaptation speed. Detail depends on what's learned in phases 1–2.
Phase 4 (sessions 21–25): evaluate post-shift adaptation. Should be faster than the original cold start.

Per-trace: extract features, run each policy, compare against ground truth, compute quality-weighted reward.

Reporting: accuracy/precision/recall per policy, learning curves, feature ablation, qualitative examples of implicit preference capture, survey alignment, approval quality distributions, preference learning curves.

Calibration analysis: initiator distribution over time, model calibration (useful vs. wasted check-ins), CLI calibration, missed check-in attribution, three-way agreement (CLI × model × user), model confidence correlation with outcomes.


## Related work

Three papers directly shaped this design.

**CowCorpus (Huq et al., 2025, arXiv 2602.17588).** 400 real-user web navigation trajectories. Four interaction styles (hands-off, hands-on, collaborative, takeover) that are stable per user across tasks. Style-conditioned models improved intervention prediction 61–63%. Validates our bet that per-developer preferences are learnable. They retrain the model; we learn a separable governance policy that works with any model. Our `session_takeover` field and per-user consistency assumption come from this.

**Grunde-McLaughlin et al. (2025, arXiv 2602.16844).** Three user studies on Computer Use Agents. Critical finding: the best trace interface (surfacing requirements + assumptions) helped developers find errors faster (Hedges' g: −0.65) but increased false confidence when wrong (g: 0.85). Developers rubber-stamp because the process *looks* reasonable. This directly threatens any trust-learning system. We took: review duration tracking as a quality signal, assumptions field in check-ins, realtime/batch distinction, and asymmetric quality weighting in the reward function (negative signals always full weight, positive signals discounted by review speed and mode).

**PAHF (Liang et al., 2026, arXiv 2602.16173).** Meta/Princeton framework for continual personalization. Pre-action clarification + post-action correction, both necessary. Post-action feedback is "particularly important for robust personalization without pre-existing user data" — our cold-start scenario exactly. We took: immediate correction injection (bridging the guideline threshold gap), drift detection design, four-phase evaluation protocol, model confidence as a logged signal. Key difference: PAHF's memory is model-internal; ours is CLI-governed. The model never writes its own rules.


## Roadmap

### Phase 1: Foundation (weeks 1–2)
- Trace logging, agents.md parser, workflow phase detection
- Blast radius computation, security-sensitive detection, change pattern classification
- Governance checks: hash validation, diff validation, scope enforcement

### Phase 2: Heuristic policy + prompt layer (week 3)
- ActionContext + feature extraction
- Heuristic policy wired into session loop
- Trust score computation + lease logic
- System prompt builder: trust summary, constraints, guidelines, recent corrections
- Check-in initiator tracking, `aa trust` / `aa history` / `aa explain`
- Behavioral guidelines table + correction-to-guideline loop
- Review duration capture + review mode tagging
- Assumptions field in check-in protocol
- Quality-weighted reward function
- Model version tracking, model confidence logging

### Phase 2b: Deferred (implement when prerequisites exist)
- Preference drift detection (needs active guidelines)
- Session takeover auto-detection (needs observed patterns)
- Model confidence as active CLI override (needs calibration data)
- Dedicated preference_hints table (needs evidence simple injection is insufficient)

### Phase 3: Data collection (weeks 3–5, concurrent)
- Daily use on own research code, target 100+ interactions
- Search for existing trace datasets (SWE-Bench traces, Copilot logs)

### Phase 4: Pair programming UX (week 4)
- Interactive diff preview, plan display with per-subtask decisions
- Session momentum, phase transitions, annotation cycle support

### Phase 5: Async delegation UX (week 5)
- Background execution, `aa status`, `aa review`, check-in queue, session summaries

### Phase 6: Learned policy (weeks 6–7)
- Context vectorization, reward computation, bandit training (LinUCB)
- Evaluate against heuristic on held-out traces, feature ablation
- Full RL only if bandit is insufficient

### Phase 7: Evaluation + paper (weeks 8–10)
- Full evaluation protocol, survey analysis, implicit preference examples
- Paper: problem (survey + lit) → design → evaluation → findings


## Design decisions

Decisions worth recording because they'll need revisiting:

| Decision | Current | Revisit if... |
|---|---|---|
| Learning algorithm | Contextual bandit (LinUCB) | Strong sequential dependencies within sessions |
| Features | Hand-crafted | Feature engineering becomes a bottleneck |
| Change pattern classification | Rule-based | Rules miss too many patterns |
| Trust model | Weighted per (file, action, pattern) | Relational structure → knowledge graph |
| Trust decay | Exponential, ~14-day half-life | Users report stale trust |
| Lease threshold | 5 consecutive approvals | Too aggressive or conservative |
| Phase detection | Agent's intent declaration | Agent labels unreliable → use action-pattern heuristics |
| Model trust visibility | Vague summary, no scores | Model needs more to reason well, or is gaming it |
| Prompt update frequency | Per-session + phase transitions | Needs mid-phase updates, or updates too expensive |
| Initiator weighting | Equal CLI vs. model | Data shows one source is consistently better |
| Model confidence | Logged, not trusted | Correlates well with outcomes → make it active |
| Cold start | Sensible defaults, no interview | Takes too many interactions → add optional light interview |
| Guideline threshold | 3 corrections on same pattern | Too noisy or too conservative |
| Guideline authorship | CLI drafts, developer confirms | If suggestions are consistently accepted → reduce friction |
| Model writes own rules | Never | N/A — hard architectural constraint |
| Rubber-stamp threshold | < 5s review duration | 5s too aggressive → adjust per task complexity |
| Approval quality discount | 0.5x rubber-stamp, 0.7x batch | Starves learning or corrupts trust |
| Correction feedback | Last 5 from traces table | Too noisy → build dedicated hints table |
| Drift detection | Deferred, 2 contradictions planned | N/A until guidelines active |
| Takeover detection | Manual flag | Patterns observed → git watcher |


## Project structure

Current prototype layout:

```
dynamic_autonomy_mvp/
├── sc/
│   ├── cli.py                # command registration only
│   ├── commands/
│   │   ├── admin.py          # init/doctor/config/rules/admin commands
│   │   ├── observe.py        # traces/report/explain/demo commands
│   │   └── shared.py         # shared command helpers (repo/db resolution)
│   ├── run/
│   │   ├── command.py        # top-level run orchestration
│   │   ├── read_stage.py     # read permission/policy flow
│   │   ├── apply_stage.py    # write policy + apply/verify flow
│   │   ├── model.py          # model check-ins, phase transitions, retries
│   │   ├── traces.py         # trace persistence helpers
│   │   ├── reporting.py      # end-of-run summary + guideline suggestions
│   │   ├── ui.py             # CLI prompts and rendering
│   │   └── helpers.py        # shared run-stage helpers
│   ├── trust_db.py           # SQLite schema + data access layer
│   ├── policy.py             # heuristic policy scoring
│   ├── prompt_builder.py     # dynamic system prompt builder
│   ├── constraints.py        # rules parser/import helpers
│   └── ...                   # schema/session/config/repo/features/verification
├── tests/
│   └── test_*.py             # unit tests for DB/policy/parser/prompt/phase
├── docs/
│   └── READING_ORDER.md      # onboarding path for new contributors
├── README.md
└── SPEC.md
```

Post-demo (optional) target refactor:
- split `trust_db.py` into `trust_schema.py` + `trust_queries.py` + `trust_metrics.py`
- add `policy_bandit.py` and offline replay evaluator behind feature flag
