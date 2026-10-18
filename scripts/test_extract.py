import sys
import time
from pathlib import Path

# Ensure the project root is on the import path so we can import app modules.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.extract import extract_from_video

def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_extract.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]

    # Store elapsed times per stage reported via the progress callback.
    stage_times = {}
    _prev_stage = None
    _prev_time = None

    def progress(stage: str):
        nonlocal _prev_stage, _prev_time
        now = time.time()
        if _prev_stage is not None and _prev_time is not None:
            stage_times[_prev_stage] = now - _prev_time
        print(f"[Stage] {stage}")
        _prev_stage = stage
        _prev_time = now

    # Run extraction – progress will fill stage_times.
    result = extract_from_video(video_path, progress=progress)

    # Capture the last stage duration (from its start to now).
    if _prev_stage is not None and _prev_time is not None:
        stage_times[_prev_stage] = time.time() - _prev_time

    # Print results.
    print("\n=== Transcript ===")
    print(result.get("transcript", "") or "(none)")

    print("\n=== OCR Text ===")
    print(result.get("ocr_text", "") or "(none)")

    print("\n=== Warnings ===")
    warnings = result.get("warnings", [])
    if warnings:
        for w in warnings:
            print(f"- {w}")
    else:
        print("(none)")

    print("\n=== Elapsed time per stage ===")
    for stage, elapsed in stage_times.items():
        print(f"{stage}: {elapsed:.2f}s")

if __name__ == "__main__":
    main()
