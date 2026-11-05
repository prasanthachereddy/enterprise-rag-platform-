"""Run every project check in order and report one summary."""

import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    name: str
    command: list[str]


@dataclass(frozen=True)
class StepResult:
    name: str
    passed: bool
    seconds: float


def default_steps(python: str, with_cdk: bool) -> list[Step]:
    steps = [
        Step("ruff", [python, "-m", "ruff", "check", "src", "tests", "scripts", "app", "infra"]),
        Step("mypy", [python, "-m", "mypy", "src", "infra"]),
        Step("pytest", [python, "-m", "pytest", "-q"]),
    ]
    if with_cdk:
        steps += [
            Step("build lambda bundle", [python, "scripts/build_lambda.py"]),
            Step("cdk synth", ["cdk", "synth", "--quiet"]),
        ]
    return steps


def run_steps(
    steps: list[Step],
    runner: Callable[[list[str]], int],
    clock: Callable[[], float] = time.monotonic,
) -> list[StepResult]:
    """Run every step even if an earlier one fails, so one run shows all problems."""
    results = []
    for step in steps:
        started = clock()
        code = runner(step.command)
        results.append(StepResult(step.name, code == 0, clock() - started))
    return results


def format_summary(results: list[StepResult]) -> str:
    lines = ["", "Verification summary", "--------------------"]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"{status}  {result.name} ({result.seconds:.1f}s)")
    failed = sum(1 for r in results if not r.passed)
    lines.append("All checks passed." if not failed else f"{failed} check(s) failed.")
    return "\n".join(lines)