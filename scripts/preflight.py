"""Run environment checks before starting the API."""

import argparse
from pathlib import Path

from app.core.preflight import run_preflight


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--load-models",
        action="store_true",
        help="Load configured Hugging Face models; may download large files.",
    )
    args = parser.parse_args()

    checks = run_preflight(ROOT, load_models=args.load_models)
    for check in checks:
        print(f"[{'PASS' if check.ok else 'FAIL'}] {check.name}: {check.detail}")
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
