"""Test harness for :func:`app.verify.verify_claim`.

Usage:
    python scripts/test_verify.py "<claim>"

Creates a minimal :class:`str` claim, runs ``verify_claim`` and prints the
resulting :class:`VerifiedClaim` as pretty‑printed JSON.
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure the repository root is on ``sys.path`` so ``app`` imports work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.verify import verify_claim


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run verify_claim on a single claim string")
    parser.add_argument("claim", help="The claim text to verify")
    args = parser.parse_args(argv)
    result = verify_claim(args.claim)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
