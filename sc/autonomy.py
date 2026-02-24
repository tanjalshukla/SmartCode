from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
import json
from pathlib import PurePosixPath
import re


_CHECKIN_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "api": ("api", "endpoint", "interface", "contract"),
    "signature": ("signature", "function signature", "method signature"),
    "schema": ("schema", "migration", "data model", "database schema", "db schema"),
    "security": ("security", "auth", "authorization", "credential", "secret"),
    "architecture": ("architecture", "architectural"),
    "config": ("config", "configuration", ".env", "settings"),
    "test": ("test", "tests", "pytest", "unit test"),
    "deployment": ("deploy", "deployment", "release", "rollout"),
}

_PREFER_AUTONOMY_PATTERNS = (
    re.compile(r"\bproceed autonom\w*\b"),
    re.compile(r"\bwithout check-?ins?\b"),
    re.compile(r"\bfewer check-?ins?\b"),
    re.compile(r"\bminimi[sz]e\s+(?:interruptions?|check-?ins?)\b"),
    re.compile(r"\blow[- ]risk\b.*\bautonom\w*\b"),
    re.compile(r"\bauto-?approve\b"),
    re.compile(r"\bskip check-?ins?\b"),
    re.compile(r"\bdon['']t ask about\b"),
    re.compile(r"\btrust me\b"),
    re.compile(r"\bjust do it\b"),
    re.compile(r"\bjust go ahead\b"),
    re.compile(r"\bgo ahead\b"),
    re.compile(r"\bstop asking\b"),
    re.compile(r"\bstop checking in\b"),
    re.compile(r"\bdo(?:n't| not) bother\b"),
    re.compile(r"\byou decide\b"),
    re.compile(r"\byour call\b"),
    re.compile(r"\bdo whatever\b"),
    re.compile(r"\bi don'?t care\b"),
    re.compile(r"\bleave me alone\b"),
)

_ONLY_CHECKIN_FOR_PATTERN = re.compile(r"only\s+check-?\s*in\s+for\s+([^.!?;]+)")
_NEGATION_CONSTRAINT_PATTERN = re.compile(r"\b(do not|don't|never)\s+change\b")
_PATH_TOKEN_PATTERN = re.compile(r"\b[\w\-\./\*]+\b")


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _normalize_scope_token(token: str) -> str | None:
    cleaned = token.strip().strip(".,:;()[]{}\"'")
    if "/" not in cleaned:
        return None
    norm = str(PurePosixPath(cleaned))
    if not norm or norm == "." or norm.startswith("../"):
        return None
    return norm


def _extract_scope_tokens(text: str) -> tuple[str, ...]:
    scopes: set[str] = set()
    for token in _PATH_TOKEN_PATTERN.findall(text):
        normalized = _normalize_scope_token(token)
        if normalized:
            scopes.add(normalized)
    return tuple(sorted(scopes))


def _contains_topic(text: str, phrase: str) -> bool:
    if " " in phrase:
        return phrase in text
    return bool(re.search(rf"\b{re.escape(phrase)}\b", text))


def _extract_topics(text: str) -> set[str]:
    discovered: set[str] = set()
    for topic, hints in _CHECKIN_TOPIC_KEYWORDS.items():
        if any(_contains_topic(text, hint) for hint in hints):
            discovered.add(topic)
    return discovered


@dataclass(frozen=True)
class AutonomyPreferences:
    prefer_fewer_checkins: bool = False
    allowed_checkin_topics: tuple[str, ...] = ()
    skip_low_risk_plan_checkpoint: bool = False
    scoped_paths: tuple[str, ...] = ()

    def to_json(self) -> str:
        payload = {
            "prefer_fewer_checkins": self.prefer_fewer_checkins,
            "allowed_checkin_topics": list(self.allowed_checkin_topics),
            "skip_low_risk_plan_checkpoint": self.skip_low_risk_plan_checkpoint,
            "scoped_paths": list(self.scoped_paths),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str | None) -> "AutonomyPreferences":
        if not raw:
            return cls()
        try:
            data = json.loads(raw)
        except Exception:
            return cls()
        topics = data.get("allowed_checkin_topics") or []
        normalized_topics = tuple(
            sorted(
                {
                    str(topic).strip().lower()
                    for topic in topics
                    if str(topic).strip().lower() in _CHECKIN_TOPIC_KEYWORDS
                }
            )
        )
        scoped_paths = data.get("scoped_paths") or []
        normalized_scopes = tuple(
            sorted(
                {
                    normalized
                    for item in scoped_paths
                    if (normalized := _normalize_scope_token(str(item))) is not None
                }
            )
        )
        return cls(
            prefer_fewer_checkins=bool(data.get("prefer_fewer_checkins", False)),
            allowed_checkin_topics=normalized_topics,
            skip_low_risk_plan_checkpoint=bool(data.get("skip_low_risk_plan_checkpoint", False)),
            scoped_paths=normalized_scopes,
        )

    def prompt_lines(self) -> list[str]:
        lines: list[str] = []
        if self.prefer_fewer_checkins:
            lines.append("Prefer autonomous execution for low-risk refactors.")
        if self.allowed_checkin_topics:
            topic_text = ", ".join(self.allowed_checkin_topics)
            lines.append(f"Check in only for: {topic_text}.")
        if self.skip_low_risk_plan_checkpoint:
            lines.append("Skip plan checkpoints for low-risk multi-file cleanups.")
        if self.scoped_paths:
            lines.append(f"Preference scope: {', '.join(self.scoped_paths)}.")
        return lines


def _scope_matches(file_path: str, scopes: tuple[str, ...]) -> bool:
    if not scopes:
        return True
    norm_path = str(PurePosixPath(file_path))
    for scope in scopes:
        if "*" in scope and fnmatch(norm_path, scope):
            return True
        if norm_path == scope:
            return True
        prefix = scope.rstrip("/")
        if prefix and norm_path.startswith(prefix + "/"):
            return True
    return False


def update_preferences_from_feedback(
    current: AutonomyPreferences,
    feedback_text: str,
) -> tuple[AutonomyPreferences, list[str]]:
    text = _normalize(feedback_text)
    if not text:
        return current, []

    prefer_fewer = current.prefer_fewer_checkins
    allowed = set(current.allowed_checkin_topics)
    skip_plan = current.skip_low_risk_plan_checkpoint
    scoped_paths = set(current.scoped_paths)
    learned: list[str] = []

    if _NEGATION_CONSTRAINT_PATTERN.search(text):
        return current, learned

    if any(pattern.search(text) for pattern in _PREFER_AUTONOMY_PATTERNS):
        if not prefer_fewer:
            learned.append("prefer fewer low-risk check-ins")
        prefer_fewer = True

    clause_match = _ONLY_CHECKIN_FOR_PATTERN.search(text)
    if clause_match:
        discovered = _extract_topics(clause_match.group(1))
        if discovered:
            if tuple(sorted(discovered)) != current.allowed_checkin_topics:
                learned.append(f"check-in scope={','.join(sorted(discovered))}")
            allowed = discovered
            prefer_fewer = True
            if discovered.issubset({"api", "signature", "schema", "security", "architecture"}):
                skip_plan = True

    discovered_scopes = _extract_scope_tokens(text)
    if discovered_scopes:
        before = tuple(sorted(scoped_paths))
        scoped_paths |= set(discovered_scopes)
        if tuple(sorted(scoped_paths)) != before:
            learned.append(f"scope={','.join(sorted(discovered_scopes))}")

    if "do not show me plan" in text or "skip plan checkpoint" in text:
        if not skip_plan:
            learned.append("skip low-risk plan checkpoints")
        skip_plan = True

    updated = AutonomyPreferences(
        prefer_fewer_checkins=prefer_fewer,
        allowed_checkin_topics=tuple(sorted(allowed)),
        skip_low_risk_plan_checkpoint=skip_plan,
        scoped_paths=tuple(sorted(scoped_paths)),
    )
    return updated, learned


def preferences_from_model_payload(payload: dict[str, object]) -> AutonomyPreferences:
    topics_raw = payload.get("allowed_checkin_topics")
    topics: tuple[str, ...] = ()
    if isinstance(topics_raw, list):
        topics = tuple(
            sorted(
                {
                    str(item).strip().lower()
                    for item in topics_raw
                    if str(item).strip().lower() in _CHECKIN_TOPIC_KEYWORDS
                }
            )
        )
    scopes_raw = payload.get("scoped_paths")
    scopes: tuple[str, ...] = ()
    if isinstance(scopes_raw, list):
        scopes = tuple(
            sorted(
                {
                    normalized
                    for item in scopes_raw
                    if (normalized := _normalize_scope_token(str(item))) is not None
                }
            )
        )
    return AutonomyPreferences(
        prefer_fewer_checkins=bool(payload.get("prefer_fewer_checkins", False)),
        allowed_checkin_topics=topics,
        skip_low_risk_plan_checkpoint=bool(payload.get("skip_low_risk_plan_checkpoint", False)),
        scoped_paths=scopes,
    )


def merge_preferences(
    current: AutonomyPreferences,
    inferred: AutonomyPreferences,
) -> tuple[AutonomyPreferences, list[str]]:
    combined_topics = tuple(sorted(set(current.allowed_checkin_topics) | set(inferred.allowed_checkin_topics)))
    combined_scopes = tuple(sorted(set(current.scoped_paths) | set(inferred.scoped_paths)))
    updated = AutonomyPreferences(
        prefer_fewer_checkins=current.prefer_fewer_checkins or inferred.prefer_fewer_checkins,
        allowed_checkin_topics=combined_topics,
        skip_low_risk_plan_checkpoint=(
            current.skip_low_risk_plan_checkpoint or inferred.skip_low_risk_plan_checkpoint
        ),
        scoped_paths=combined_scopes,
    )
    learned: list[str] = []
    if updated.prefer_fewer_checkins and not current.prefer_fewer_checkins:
        learned.append("prefer fewer low-risk check-ins")
    if updated.allowed_checkin_topics != current.allowed_checkin_topics and updated.allowed_checkin_topics:
        learned.append(f"check-in scope={','.join(updated.allowed_checkin_topics)}")
    if updated.skip_low_risk_plan_checkpoint and not current.skip_low_risk_plan_checkpoint:
        learned.append("skip low-risk plan checkpoints")
    if updated.scoped_paths != current.scoped_paths and updated.scoped_paths:
        learned.append(f"scope={','.join(updated.scoped_paths)}")
    return updated, learned


def adjusted_policy_thresholds(
    proceed_threshold: float,
    flag_threshold: float,
    preferences: AutonomyPreferences,
    *,
    file_path: str | None = None,
    model_checkin_approval_rate: float | None = None,
    model_checkin_total: int = 0,
) -> tuple[float, float]:
    adjusted_proceed = proceed_threshold
    adjusted_flag = flag_threshold

    autonomy_applies = preferences.prefer_fewer_checkins and (
        file_path is None or _scope_matches(file_path, preferences.scoped_paths)
    )
    if autonomy_applies:
        delta = 0.25
        if preferences.allowed_checkin_topics:
            delta += 0.10
        adjusted_proceed -= delta
        adjusted_flag -= delta

    if model_checkin_total >= 5 and model_checkin_approval_rate is not None and model_checkin_approval_rate < 0.40:
        adjusted_proceed += 0.15
        adjusted_flag += 0.15

    adjusted_proceed = max(adjusted_proceed, -0.5)
    adjusted_flag = max(adjusted_flag, -0.5)
    if adjusted_flag > adjusted_proceed:
        adjusted_flag = adjusted_proceed
    return adjusted_proceed, adjusted_flag
