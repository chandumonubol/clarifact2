"""Test script for compute_credibility_score.
"""
import sys
import os
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import json
from app.score import compute_credibility_score

sample_claims = [
    {"verdict": "supported", "text": "sample claim 1"},
    {"verdict": "unverified", "text": "sample claim 2"},
    {"verdict": "misleading", "text": "sample claim 3"},
    {"verdict": "contradicted", "text": "sample claim 4"},
]

promo = {"detected": True, "type": "hidden", "evidence": []}
result = compute_credibility_score(sample_claims, promo, text_len=200)
print(json.dumps(result, indent=2))
