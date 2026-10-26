"""Test script for verify_claim with a sample claim.

Runs the verification pipeline for a sample claim and prints the result as JSON.
"""
import json
import sys
import os

# Ensure repository root is in PYTHONPATH (should be by default when running from repo root)
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from app.verify import verify_claim

if __name__ == "__main__":
    sample_claim = "World Health Organization projections on diabetes prevalence by 2040, 700 million cases"
    result = verify_claim(sample_claim)
    print(json.dumps(result, indent=2))
