from __future__ import annotations

"""Run-finalization helpers: summaries and guideline suggestion prompts."""

from rich import print
from rich.prompt import Prompt

from ..trust_db import TrustDB
from .ui import _render_file_list


def _render_run_summary(
    *,
    trust_db: TrustDB,
    repo_root: str,
    session_id: str,
) -> None:
    rows = trust_db.session_traces(repo_root, session_id)
    if not rows:
        return
    check_ins = sum(1 for row in rows if row["action_type"] == "check_in")
    apply_files = sorted(
        {
            str(row["file_path"])
            for row in rows
            if row["stage"] == "apply" and str(row["file_path"]) != "__session__"
        }
    )
    changed_patterns = sorted(
        {
            str(row["change_type"])
            for row in rows
            if row["stage"] == "apply"
            and row["change_type"] is not None
            and str(row["change_type"]).strip()
        }
    )
    print("\n[bold]Run complete[/bold]")
    if apply_files:
        print("Updated files:")
        _render_file_list(apply_files)
    if check_ins:
        label = "check-in" if check_ins == 1 else "check-ins"
        print(f"{check_ins} {label} during run.")
    if changed_patterns:
        print("Change patterns:")
        for pattern in changed_patterns:
            print(f"  - {pattern}")


def _maybe_prompt_guideline_suggestions(
    *,
    trust_db: TrustDB,
    repo_root: str,
    min_count: int = 3,
) -> None:
    candidates = trust_db.guideline_candidates(repo_root, min_count=min_count, max_items=4)
    if not candidates:
        return
    print("\n[bold]Guideline suggestions from repeated feedback[/bold]")
    selected: list[str] = []
    for item in candidates:
        print(f"- ({item.count}x) {item.guideline}")
        choice = Prompt.ask(
            "Apply (a), edit then apply (e), or skip (s)?",
            choices=["a", "e", "s"],
            default="s",
        )
        if choice == "a":
            selected.append(item.guideline)
        elif choice == "e":
            edited = Prompt.ask("Edited guideline", default=item.guideline).strip()
            if edited:
                selected.append(edited)
    if not selected:
        return
    inserted = trust_db.add_behavioral_guidelines(
        repo_root,
        source="feedback_auto",
        guidelines=selected,
    )
    if inserted:
        print(f"[green]Added {inserted} behavioral guideline(s).[/green]")


def _finalize_run(
    *,
    trust_db: TrustDB,
    repo_root: str,
    session_id: str,
) -> None:
    _render_run_summary(
        trust_db=trust_db,
        repo_root=repo_root,
        session_id=session_id,
    )
    _maybe_prompt_guideline_suggestions(
        trust_db=trust_db,
        repo_root=repo_root,
    )
