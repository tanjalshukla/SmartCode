from __future__ import annotations

import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    passed: bool
    output: str


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    checks: tuple[VerificationCheck, ...]
    expected_behavior: str

    def checks_json(self) -> str:
        payload = [
            {"name": check.name, "passed": check.passed, "output": check.output}
            for check in self.checks
        ]
        return json.dumps(payload)


def run_verification(
    *,
    repo_root: Path,
    touched_files: list[str],
    expected_behavior: str,
    timeout_sec: int,
    command: str | None = None,
) -> VerificationResult:
    checks: list[VerificationCheck] = []

    if command:
        try:
            argv = shlex.split(command)
            if not argv:
                raise ValueError("verification command is empty")
            result = subprocess.run(
                argv,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=max(timeout_sec, 1),
            )
            output = (result.stdout + result.stderr).strip()
            checks.append(
                VerificationCheck(
                    name="custom_verification",
                    passed=result.returncode == 0,
                    output=output or "ok",
                )
            )
        except subprocess.TimeoutExpired:
            checks.append(
                VerificationCheck(
                    name="custom_verification",
                    passed=False,
                    output="verification command timed out",
                )
            )
        except Exception as exc:
            checks.append(
                VerificationCheck(
                    name="custom_verification",
                    passed=False,
                    output=str(exc),
                )
            )

    python_files = [path for path in touched_files if path.endswith(".py")]
    if python_files:
        cmd = [sys.executable, "-m", "py_compile", *python_files]
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=max(timeout_sec, 1),
            )
            output = (result.stdout + result.stderr).strip()
            checks.append(
                VerificationCheck(
                    name="python_syntax",
                    passed=result.returncode == 0,
                    output=output or "ok",
                )
            )
        except subprocess.TimeoutExpired:
            checks.append(
                VerificationCheck(
                    name="python_syntax",
                    passed=False,
                    output="verification timed out",
                )
            )
        except Exception as exc:
            checks.append(
                VerificationCheck(
                    name="python_syntax",
                    passed=False,
                    output=str(exc),
                )
            )

    if not checks:
        checks.append(
            VerificationCheck(
                name="sanity",
                passed=True,
                output="no language-specific checks required",
            )
        )

    passed = all(check.passed for check in checks)
    return VerificationResult(
        passed=passed,
        checks=tuple(checks),
        expected_behavior=expected_behavior,
    )
