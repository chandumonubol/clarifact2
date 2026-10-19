"""Configuration module for ClariFact.
Loads environment variables from the repository root .env file using python-dotenv.
Exports module-level variables for LLM provider settings and the FactCheck API key.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Determine repository root (parent of this file's directory)
_REPO_ROOT = Path(__file__).resolve().parent.parent
# Load .env if present; missing file is ignored
_load_result = load_dotenv(dotenv_path=_REPO_ROOT / ".env")

# Defaults per specification
DEFAULTS = {
    "LLM_PROVIDER": "ollama",
    "OLLAMA_URL": "http://localhost:11434",
    "OLLAMA_MODEL": "qwen2.5:3b",
    "GEMINI_API_KEY": "",
    "GEMINI_MODEL": "",
    "GROQ_API_KEY": "",
    "GROQ_MODEL": "",
    "FACTCHECK_API_KEY": "",
}

# Exported configuration values (module‑level)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", DEFAULTS["LLM_PROVIDER"]).lower()
OLLAMA_URL = os.getenv("OLLAMA_URL", DEFAULTS["OLLAMA_URL"]).rstrip('/')
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", DEFAULTS["OLLAMA_MODEL"]).strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", DEFAULTS["GEMINI_API_KEY"]).strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", DEFAULTS["GEMINI_MODEL"]).strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", DEFAULTS["GROQ_API_KEY"]).strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", DEFAULTS["GROQ_MODEL"]).strip()
FACTCHECK_API_KEY = os.getenv("FACTCHECK_API_KEY", DEFAULTS["FACTCHECK_API_KEY"]).strip()

# The module deliberately does not expose any function that prints secrets.
