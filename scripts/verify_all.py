"""One command to verify the project: python scripts\\verify_all.py [--with-cdk]"""

import argparse
import shutil
import subprocess
import sys

from enterprise_rag.verification import default_steps, format_summary, run_steps


def run_command(command: list[str]) -> int:
    resolved = shutil.which(command[0]) or command[0]
    print(f"\n> {' '.join(command)}", flush=True)
    return subprocess.run([resolved, *command[1:]], check=False).returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Run lint, types, tests and optional CDK synth")
    parser.add_argument("--with-cdk", action="store_true", help="also build the bundle and synth")
    args = parser.parse_args()
    results = run_steps(default_steps(sys.executable, args.with_cdk), run_command)
    print(format_summary(results))
    sys.exit(0 if all(r.passed for r in results) else 1)


if __name__ == "__main__":
    main()