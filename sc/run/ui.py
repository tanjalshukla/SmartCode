from __future__ import annotations

"""Terminal-facing prompts and rendering helpers for `sc run`."""

from rich import print
from rich.prompt import Prompt

from ..policy import PolicyDecision
from ..schema import IntentDeclaration, WorkflowPhase
from ..trust_db import PolicyHistory


def _render_file_list(files: list[str]) -> None:
    for path in files:
        print(f"  - {path}")


def _prompt_optional_feedback(prompt_text: str) -> str | None:
    note = Prompt.ask(prompt_text, default="").strip()
    return note or None


def _prompt_approval(
    stage: str,
    files: list[str],
    allow_remember: bool,
) -> tuple[bool, bool, str | None]:
    print(f"\n[bold]Approval required ({stage})[/bold]")
    print("Agent requests to modify:")
    _render_file_list(files)
    choices = ["a", "d"]
    if allow_remember:
        choices.insert(1, "r")
        prompt = "Approve once (a), approve & remember (r), deny (d)"
    else:
        prompt = "Approve once (a), deny (d)"
    response = Prompt.ask(prompt, choices=choices, default="d")
    if response == "a":
        return True, False, None
    if response == "r":
        note = _prompt_optional_feedback("Optional note for future autonomy decisions")
        return True, True, note
    note = _prompt_optional_feedback("Optional reason for denial")
    return False, False, note


def _prompt_read(files: list[str], reason: str | None) -> tuple[bool, str | None]:
    print("\n[bold]Read request[/bold]")
    if reason:
        print(f"Reason: {reason}")
    print("Agent requests to read:")
    _render_file_list(files)
    response = Prompt.ask("Approve (a) or deny (d)", choices=["a", "d"], default="d")
    if response == "a":
        return True, None
    note = _prompt_optional_feedback("Optional reason for denying this read")
    return False, note


def _render_intent_summary(declaration: IntentDeclaration) -> None:
    print("\n[bold]Intent summary[/bold]")
    print(f"Task summary: {declaration.task_summary}")
    print(f"Planned actions: {', '.join(declaration.planned_actions) or 'none'}")
    if declaration.notes:
        print(f"Plan: {declaration.notes}")
    print("Planned files:")
    _render_file_list(declaration.planned_files)


def _prompt_plan_checkpoint(
    declaration: IntentDeclaration,
    reasons: tuple[str, ...],
) -> tuple[str, str | None]:
    print("\n[bold]Plan checkpoint required[/bold]")
    _render_intent_summary(declaration)
    if reasons:
        print("Why this needs explicit plan approval:")
        for reason in reasons:
            print(f"  - {reason}")
    decision = Prompt.ask(
        "Approve plan (a), request revision (v), or deny task (d)",
        choices=["a", "v", "d"],
        default="d",
    )
    if decision == "a":
        return "approve", None
    if decision == "v":
        note = _prompt_optional_feedback("What should the plan change?")
        return "revise", note
    note = _prompt_optional_feedback("Optional reason for denying this task")
    return "deny", note


def _prompt_permanent(files: list[str]) -> bool:
    print("\n[bold]Grant indefinite permission?[/bold]")
    print("These files have been approved repeatedly:")
    _render_file_list(files)
    response = Prompt.ask("Allow auto-apply for future changes (y/n)", choices=["y", "n"], default="n")
    return response == "y"


def _confirm_read_missing(missing_files: list[str]) -> bool:
    print("\n[bold yellow]Read request includes missing files[/bold yellow]")
    _render_file_list(missing_files)
    response = Prompt.ask("Continue anyway? (a)pprove/(d)eny", choices=["a", "d"], default="d")
    return response == "a"


def _confirm_create_files(missing_files: list[str]) -> bool:
    print("\n[bold yellow]Patch will create new files[/bold yellow]")
    _render_file_list(missing_files)
    response = Prompt.ask("Allow new file creation? (a)pprove/(d)eny", choices=["a", "d"], default="d")
    return response == "a"


def _render_policy_snapshot(
    *,
    stage: str,
    files: list[str],
    histories: dict[str, PolicyHistory],
    policies: dict[str, PolicyDecision],
) -> None:
    if not files:
        return
    print(f"\n[bold]Policy snapshot ({stage})[/bold]")
    for path in files:
        policy = policies.get(path)
        history = histories.get(path)
        if policy is None or history is None:
            continue
        print(
            f"- {path}: {policy.action} (score={policy.score:.2f}, "
            f"approvals={history.approvals}, weighted={history.effective_approvals:.1f}, "
            f"rubber={history.rubber_stamp_approvals}, denials={history.denials})"
        )


def _show_system_prompt(phase: WorkflowPhase, prompt_text: str) -> None:
    print(f"\n[bold]System prompt ({phase})[/bold]")
    print(prompt_text)
