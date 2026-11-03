"""Build build\\lambda: the handler code plus beautifulsoup4, ready for CDK to zip and upload."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "build" / "lambda"
SOURCE = ROOT / "src" / "enterprise_rag"
PACKAGES = ["ingestion", "observability", "cloud"]


def main() -> None:
    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--target", str(TARGET),
         "beautifulsoup4>=4.12,<5.0"],
        check=True,
    )  # fmt: skip
    package = TARGET / "enterprise_rag"
    package.mkdir()
    shutil.copy2(SOURCE / "__init__.py", package / "__init__.py")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in PACKAGES:
        shutil.copytree(SOURCE / name, package / name, ignore=ignore)
    print(f"Built {TARGET}")


if __name__ == "__main__":
    main()