"""Pure sensors; never execute untrusted learner code."""

import math

from ailearn.models import SensorResult


def numeric(actual: float, expected: float, tolerance: float = 1e-6) -> SensorResult:
    if tolerance < 0 or not math.isfinite(tolerance):
        raise ValueError("tolerance must be finite and nonnegative")
    passed = (
        math.isfinite(actual)
        and math.isfinite(expected)
        and math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance)
    )
    return SensorResult(
        name="numeric",
        passed=passed,
        details=f"actual={actual}; expected={expected}; tolerance={tolerance}",
    )


def shape(actual: list[int], expected: list[int]) -> SensorResult:
    return SensorResult(
        name="shape", passed=actual == expected, details=f"actual={actual}; expected={expected}"
    )


def finite(values: list[float]) -> SensorResult:
    return SensorResult(
        name="finite",
        passed=bool(values) and all(map(math.isfinite, values)),
        details="Checks nonempty numerical values for NaN and infinity.",
    )


def units(actual: str, expected: str) -> SensorResult:
    return SensorResult(
        name="units",
        passed=actual.strip() == expected.strip(),
        details=f"actual={actual}; expected={expected}",
    )


def split(train: list[int], test: list[int], temporal: bool = False) -> SensorResult:
    passed = bool(train and test) and not set(train) & set(test)
    if temporal and passed:
        passed = max(train) < min(test)
    return SensorResult(
        name="split",
        passed=passed,
        details="Train/test IDs must be disjoint; temporal IDs must be ordered.",
    )


def feature_availability(available_at: list[int], prediction_at: int) -> SensorResult:
    return SensorResult(
        name="feature-availability",
        passed=bool(available_at) and all(t <= prediction_at for t in available_at),
        details="All features must be available by the prediction time.",
    )


def baseline(model: float, reference: float, higher_is_better: bool = False) -> SensorResult:
    passed = math.isfinite(model) and math.isfinite(reference)
    passed = passed and (model > reference if higher_is_better else model < reference)
    return SensorResult(
        name="baseline", passed=passed, details=f"model={model}; baseline={reference}"
    )


def run(spec: dict) -> list[SensorResult]:
    if not isinstance(spec, dict) or not spec:
        raise ValueError("sensor input must be a nonempty object")
    registry = {
        "numeric": numeric,
        "shape": shape,
        "finite": finite,
        "units": units,
        "split": split,
        "feature-availability": feature_availability,
        "baseline": baseline,
    }
    results = []
    for name, arguments in spec.items():
        if name not in registry:
            raise ValueError(f"unknown sensor: {name}")
        results.append(registry[name](**arguments))
    return results
