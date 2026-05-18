from __future__ import annotations

from typing import Any, Dict, Optional


class ConstraintAssemblyError(Exception):
    """Base error for constraint assembly solving."""

    def __init__(self, message: str, *, report: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.report = report


class ConstraintSchemaError(ConstraintAssemblyError):
    pass


class SubSpecCycleError(ConstraintSchemaError):
    """Raised when sub_spec file references form a cycle."""


class ConstraintValidationError(ConstraintAssemblyError):
    pass


class ConstraintSolveError(ConstraintAssemblyError):
    pass
