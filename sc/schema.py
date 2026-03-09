from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .phase import WorkflowPhase


ChangeType = Literal[
    "general_change",
    "documentation",
    "test_generation",
    "config_change",
    "api_change",
    "data_model_change",
    "dependency_update",
    "error_handling",
]


class ReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["read_request"]
    files: list[str]
    reason: str | None = None

    @field_validator("files")
    @classmethod
    def validate_files(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for path in value:
            if not path or path.strip() == "":
                raise ValueError("files cannot contain empty paths")
            if Path(path).is_absolute():
                raise ValueError("files must be repo-relative")
            norm = str(Path(path))
            if norm.startswith(".."):
                raise ValueError("files must not escape repo")
            normalized.append(norm)
        return normalized


class IntentDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_summary: str
    planned_files: list[str]
    planned_actions: list[Literal["edit_code", "add_tests", "run_tests"]]
    planned_commands: list[str]
    workflow_phase: WorkflowPhase | None = None
    notes: str | None = None
    expected_change_types: list[ChangeType] = Field(default_factory=list)
    requirements_covered: list[str] = Field(default_factory=list)
    potential_deviations: list[str] = Field(default_factory=list)

    @field_validator("planned_files")
    @classmethod
    def validate_planned_files(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for path in value:
            if not path or path.strip() == "":
                raise ValueError("planned_files cannot contain empty paths")
            if Path(path).is_absolute():
                raise ValueError("planned_files must be repo-relative")
            norm = str(Path(path))
            if norm.startswith(".."):
                raise ValueError("planned_files must not escape repo")
            normalized.append(norm)
        return normalized


class CheckInMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["check_in"]
    reason: str
    check_in_type: Literal[
        "plan_review",
        "decision_point",
        "progress_update",
        "deviation_notice",
        "phase_transition",
        "uncertainty",
    ]
    content: str
    recommendation: str | None = None
    options: list[str] | None = None
    assumptions: list[str] | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
