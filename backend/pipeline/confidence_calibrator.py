"""
Post-hoc confidence calibration (deterministic bin map).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class IsotonicCalibrator:
    """
    Lightweight calibration map inspired by isotonic post-hoc calibration.
    """

    calibration_map: Dict[Tuple[float, float], float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.calibration_map is None:
            self.calibration_map = {
                (0.90, 1.00): 0.95,
                (0.80, 0.90): 0.87,
                (0.70, 0.80): 0.78,
                (0.60, 0.70): 0.68,
                (0.50, 0.60): 0.57,
                (0.40, 0.50): 0.45,
                (0.00, 0.40): 0.30,
            }

    def calibrate(self, raw_score: float) -> float:
        s = max(0.0, min(1.0, float(raw_score)))
        for (low, high), calibrated in self.calibration_map.items():
            if low <= s <= high:
                return round(calibrated, 2)
        return round(s, 2)

