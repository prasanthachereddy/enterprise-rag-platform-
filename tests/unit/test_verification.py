from enterprise_rag.verification import Step, default_steps, format_summary, run_steps


def test_default_steps_add_cdk_checks_only_when_asked() -> None:
    plain = [s.name for s in default_steps("python", with_cdk=False)]
    full = [s.name for s in default_steps("python", with_cdk=True)]
    assert plain == ["ruff", "mypy", "pytest"]
    assert full == [*plain, "build lambda bundle", "cdk synth"]


def test_every_step_runs_even_after_a_failure() -> None:
    steps = [Step("a", ["a"]), Step("b", ["b"]), Step("c", ["c"])]
    codes = {"a": 0, "b": 1, "c": 0}
    seen: list[str] = []

    def runner(command: list[str]) -> int:
        seen.append(command[0])
        return codes[command[0]]

    results = run_steps(steps, runner, clock=iter([0.0, 1.0, 1.0, 3.0, 3.0, 4.5]).__next__)
    assert seen == ["a", "b", "c"]
    assert [r.passed for r in results] == [True, False, True]
    summary = format_summary(results)
    assert "PASS  a (1.0s)" in summary
    assert "FAIL  b (2.0s)" in summary
    assert "1 check(s) failed." in summary


def test_summary_says_all_passed() -> None:
    results = run_steps([Step("a", ["a"])], lambda command: 0)
    assert "All checks passed." in format_summary(results)