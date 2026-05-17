from __future__ import annotations

from typing import Any

from .errors import ConstraintSchemaError

# Default caps for a single CONSTRAINTS graph (override via spec["limits"]).
DEFAULT_MAX_BODIES = 40
WARN_BODIES = 30
DEFAULT_MAX_CONSTRAINTS = 240
ABSOLUTE_MAX_BODIES = 64
ABSOLUTE_MAX_CONSTRAINTS = 400


def resolve_limits(spec: dict[str, Any]) -> dict[str, int]:
    raw = spec.get("limits")
    if raw is None:
        return {
            "max_bodies": DEFAULT_MAX_BODIES,
            "max_constraints": DEFAULT_MAX_CONSTRAINTS,
            "warn_bodies": WARN_BODIES,
        }
    if not isinstance(raw, dict):
        raise ConstraintSchemaError("limits must be an object")
    max_bodies = int(raw.get("max_bodies", DEFAULT_MAX_BODIES))
    max_constraints = int(raw.get("max_constraints", DEFAULT_MAX_CONSTRAINTS))
    warn_bodies = int(raw.get("warn_bodies", WARN_BODIES))
    if max_bodies < 2:
        raise ConstraintSchemaError("limits.max_bodies must be >= 2")
    if max_constraints < 1:
        raise ConstraintSchemaError("limits.max_constraints must be >= 1")
    if max_bodies > ABSOLUTE_MAX_BODIES:
        raise ConstraintSchemaError(f"limits.max_bodies must be <= {ABSOLUTE_MAX_BODIES}")
    if max_constraints > ABSOLUTE_MAX_CONSTRAINTS:
        raise ConstraintSchemaError(f"limits.max_constraints must be <= {ABSOLUTE_MAX_CONSTRAINTS}")
    return {
        "max_bodies": max_bodies,
        "max_constraints": max_constraints,
        "warn_bodies": min(warn_bodies, max_bodies),
    }


def check_assembly_scale(
    *,
    body_count: int,
    constraint_count: int,
    limits: dict[str, int],
) -> list[str]:
    warnings: list[str] = []
    if body_count > limits["max_bodies"]:
        raise ConstraintSchemaError(
            f"bodies count {body_count} exceeds limits.max_bodies={limits['max_bodies']}; "
            "split into sub-chains or raise limits explicitly"
        )
    if constraint_count > limits["max_constraints"]:
        raise ConstraintSchemaError(
            f"constraints count {constraint_count} exceeds limits.max_constraints={limits['max_constraints']}"
        )
    if body_count > limits["warn_bodies"]:
        warnings.append(
            f"large_assembly: {body_count} bodies (warn threshold {limits['warn_bodies']}); "
            "prefer sub-chains or hybrid Location placement"
        )
    return warnings
