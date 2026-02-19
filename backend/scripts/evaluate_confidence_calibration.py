"""
Evaluate confidence calibration metrics (ECE, Brier score).

Input format (JSONL):
{"confidence": 0.96, "correct": 1}
{"confidence": 0.62, "correct": 0}

Usage:
  uv run python scripts/evaluate_confidence_calibration.py --input data/calibration/validation.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple


def load_jsonl(path: Path) -> List[Tuple[float, int]]:
    rows: List[Tuple[float, int]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            c = float(obj["confidence"])
            y = int(obj["correct"])
            rows.append((max(0.0, min(1.0, c)), 1 if y else 0))
    return rows


def brier_score(rows: List[Tuple[float, int]]) -> float:
    if not rows:
        return 0.0
    return sum((c - y) ** 2 for c, y in rows) / len(rows)


def expected_calibration_error(rows: List[Tuple[float, int]], bins: int = 10) -> float:
    if not rows:
        return 0.0
    bucketed = [[] for _ in range(bins)]
    for c, y in rows:
        idx = min(int(c * bins), bins - 1)
        bucketed[idx].append((c, y))
    n = len(rows)
    ece = 0.0
    for bucket in bucketed:
        if not bucket:
            continue
        conf_avg = sum(c for c, _ in bucket) / len(bucket)
        acc_avg = sum(y for _, y in bucket) / len(bucket)
        ece += (len(bucket) / n) * abs(conf_avg - acc_avg)
    return ece


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to JSONL calibration file")
    parser.add_argument("--bins", type=int, default=10)
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    if not rows:
        raise SystemExit("No rows found in calibration file.")

    ece = expected_calibration_error(rows, bins=args.bins)
    brier = brier_score(rows)

    print(json.dumps({
        "n": len(rows),
        "bins": args.bins,
        "ece": round(ece, 6),
        "brier_score": round(brier, 6),
    }, indent=2))


if __name__ == "__main__":
    main()

