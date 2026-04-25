from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StatValue:
    """One neutral computed stat value."""

    key: str | None
    value: str


@dataclass(frozen=True)
class ComputedStat:
    """One computed stat id plus normalized neutral values."""

    stat_id: str
    values: tuple[StatValue, ...]


@dataclass(frozen=True, init=False)
class BaseStatResult:
    """Neutral logical stat payload."""

    values: tuple[StatValue, ...]
    metadata: dict[str, object] = field(default_factory=dict)

    def __init__(self, result: object, *, metadata: dict[str, object] | None = None) -> None:
        object.__setattr__(
            self,
            "values",
            tuple(StatValue(key, value) for key, value in normalize_stat_result("stat", result)),
        )
        object.__setattr__(self, "metadata", dict(metadata or {}))


def normalize_stat_result(stat_id: str, result: object) -> tuple[tuple[str | None, str], ...]:
    """Normalize one stat return value into ``(key, value)`` pairs."""

    if isinstance(result, BaseStatResult):
        return tuple((value.key, value.value) for value in result.values)
    if not isinstance(result, dict):
        return ((None, _coerce_stat_value(stat_id, result)),)
    if not result:
        raise ValueError(f"Stat '{stat_id}' must return a non-empty dict when using named values")
    normalized: list[tuple[str | None, str]] = []
    for key, value in result.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"Stat '{stat_id}' dict keys must be non-empty strings")
        normalized.append((key, _coerce_stat_value(stat_id, value, key=key)))
    return tuple(normalized)


def compute_stat(stat_id: str, result: object) -> ComputedStat:
    """Compute one neutral stat result."""

    return ComputedStat(
        stat_id=stat_id,
        values=tuple(StatValue(key, value) for key, value in normalize_stat_result(stat_id, result)),
    )


def _coerce_stat_value(stat_id: str, value: object, *, key: str | None = None) -> str:
    text = value if isinstance(value, str) else str(value)
    if not text:
        if key is None:
            raise ValueError(f"Stat '{stat_id}' value must be non-empty after str() coercion")
        raise ValueError(f"Stat '{stat_id}' dict value for key '{key}' must be non-empty after str() coercion")
    return text
