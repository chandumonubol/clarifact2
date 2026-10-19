"""Test script for the LLM wrapper.
Usage:
    python scripts/test_llm.py "<prompt>"
It prints the provider used, the latency in seconds, and the parsed JSON result.
If the LLM call fails (e.g., Ollama not reachable) it prints a clear error message.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sys
import time
import logging
import os
import pathlib

# Ensure the repository root (parent of the scripts directory) is on sys.path.
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import config, llm

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_llm.py \"<prompt>\"")
        sys.exit(1)
    prompt = sys.argv[1]
    start = time.time()
    result = llm.llm_json(prompt)
    latency = time.time() - start

    # If result is empty, assume the call failed.
    if not result:
        print("LLM call failed or provider unreachable.")
        print(f"Provider attempted: {config.LLM_PROVIDER}")
        print(f"Latency: {latency:.2f}s")
        sys.exit(0)

    print(f"Provider: {config.LLM_PROVIDER}")
    print(f"Latency: {latency:.2f}s")
    print(result)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
