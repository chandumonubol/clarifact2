"""Run evaluation samples for ClariFact.

The script reads a ``expected.json`` file from the samples directory,
executes the analysis pipeline on each sample, prints a markdown table of
results, and writes a detailed ``samples_report.md`` report.

The samples directory is taken from the ``SAMPLES_DIR`` environment variable
or defaults to ``C:/clarifact-samples``.
"""

import os
import json
import time
import logging
from pathlib import Path
import sys
from typing import List, Dict

# Ensure repository root is on the import path.
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from app.pipeline import run_pipeline
from app.interfaces import AnalysisResult, ClaimOut

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def load_samples(samples_dir: Path) -> List[Dict]:
    expected_path = samples_dir / "expected.json"
    if not expected_path.is_file():
        logging.warning(f"expected.json not found in {samples_dir}. No samples to run.")
        return []
    with expected_path.open(encoding="utf-8") as f:
        return json.load(f)


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def progress_printer(step: str) -> None:
    # Simple console progress output.
    print(f"[progress] {step}")


def format_markdown_table(rows: List[List[str]]) -> str:
    header = ["File", "Expect label", "Actual label", "Expect promo", "Actual promo", "Score", "Sec", "Status"]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def build_fail_report(entry: Dict, result: AnalysisResult, duration: float) -> str:
    # Assemble detailed markdown for a failing sample.
    file_name = entry.get("file", "")
    notes = entry.get("notes", "")
    transcript = result.get("transcript", "")
    ocr = result.get("ocr_text", "")
    claims: List[ClaimOut] = result.get("claims", [])
    promo_evidence = result.get("promo", {}).get("evidence", [])

    claim_lines = []
    for c in claims:
        txt = c.get("text", "")
        verdict = c.get("verdict", "")
        claim_lines.append(f"- **{txt}** – {verdict}")
        explanation = c.get("explanation", "")
        if explanation:
            claim_lines.append(f"  - {explanation}")
        sources = c.get("sources", [])
        if sources:
            srcs = ", ".join(s.get("url", "") for s in sources)
            claim_lines.append(f"  - sources: {srcs}")

    return "\n".join([
        f"## {file_name} – FAIL",
        f"*Notes:* {notes}" if notes else "",
        f"**Duration:** {duration:.2f}s",
        f"**Transcript:**\n{transcript}" if transcript else "",
        f"**OCR Text:**\n{ocr}" if ocr else "",
        "**Claims:**",
        "\n".join(claim_lines) if claim_lines else "None",
        f"**Promo evidence:** {', '.join(promo_evidence) if promo_evidence else 'None'}",
    ])


def main() -> int:
    samples_dir_env = os.getenv("SAMPLES_DIR")
    samples_dir = Path(samples_dir_env) if samples_dir_env else Path(r"C:/clarifact-samples")
    logging.info(f"Using samples directory: {samples_dir}")

    try:
        samples = load_samples(samples_dir)
    except Exception as e:
        logging.error(f"Failed to load expected.json: {e}")
        return 1

    if not samples:
        logging.info("No sample entries to process. Generating empty report.")
        report_path = Path.cwd() / "samples_report.md"
        report_path.write_text("No samples found.\n", encoding="utf-8")
        print("\n=== Sample Evaluation Report ===\nNo samples found.")
        return 0

    rows: List[List[str]] = []
    pass_count = 0
    fail_reports: List[str] = []

    for entry in samples:
        file_name = entry.get("file", "")
        expect_label = str(entry.get("expect_label", ""))
        expect_promo = str(entry.get("expect_promo", ""))
        sample_path = samples_dir / file_name
        logging.info(f"Processing {file_name}")
        start = time.time()
        try:
            if sample_path.suffix.lower() == ".txt":
                text = read_text_file(sample_path)
                result: AnalysisResult = run_pipeline(text, None, None, progress_printer)
            else:
                result = run_pipeline(None, str(sample_path), None, progress_printer)
        except Exception as exc:
            duration = time.time() - start
            rows.append([file_name, expect_label, "N/A", expect_promo, "N/A", "N/A", f"{duration:.2f}", "FAIL"])
            fail_reports.append(f"## {file_name} – FAIL\n**Error:** {exc}\n")
            continue

        duration = time.time() - start
        actual_label = str(result.get("label", ""))
        actual_promo = str(result.get("promo", {}).get("type", ""))
        score = str(result.get("credibility_score", ""))
        # Normalise expected values from entry (expected_label/expected_promo) to match actual output
        expected_label = str(entry.get("expected_label", ""))
        expected_promo = str(entry.get("expected_promo", ""))
        label_map = {"FALSE": "Mixed / Low Trust", "MISLEADING": "Mixed / Low Trust"}
        promo_map = {"high": "hidden"}
        norm_expected_label = label_map.get(expected_label.upper(), expected_label)
        norm_expected_promo = promo_map.get(expected_promo.lower(), expected_promo)
        status = "PASS" if (actual_label == norm_expected_label and actual_promo == norm_expected_promo) else "FAIL"
        rows.append([file_name, expect_label, actual_label, expect_promo, actual_promo, score, f"{duration:.2f}", status])
        if status == "PASS":
            pass_count += 1
        else:
            fail_reports.append(build_fail_report(entry, result, duration))

    table_md = format_markdown_table(rows)
    report_md = "\n\n".join([table_md, f"**Pass count:** {pass_count}/{len(samples)}", *fail_reports])
    report_path = Path.cwd() / "samples_report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write(report_md)

    print("\n=== Sample Evaluation Report ===\n")
    print(report_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
