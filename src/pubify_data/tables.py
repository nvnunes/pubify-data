from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True, init=False)
class TableResult:
    """Neutral logical table payload."""

    bodies: tuple[tuple[tuple[object, ...], ...], ...]
    metadata: dict[str, object] = field(default_factory=dict)

    def __init__(self, data: object, *, metadata: dict[str, object] | None = None) -> None:
        object.__setattr__(self, "bodies", _normalize_table_data(data))
        object.__setattr__(self, "metadata", dict(metadata or {}))

    @property
    def width(self) -> int:
        return len(self.bodies[0][0])


@dataclass(frozen=True)
class ComputedTable:
    """One computed table id plus neutral table bodies."""

    table_id: str
    width: int
    bodies: tuple[tuple[tuple[object, ...], ...], ...]
    metadata: dict[str, object] = field(default_factory=dict)


def compute_table(table_id: str, result: object) -> ComputedTable:
    """Normalize one table result."""

    if not isinstance(result, TableResult):
        raise ValueError(f"Table '{table_id}' must return TableResult(...)")
    return ComputedTable(table_id=table_id, width=result.width, bodies=result.bodies, metadata=result.metadata)


def _normalize_table_data(data: object) -> tuple[tuple[tuple[object, ...], ...], ...]:
    if hasattr(data, "ndim") and hasattr(data, "tolist"):
        ndim = getattr(data, "ndim")
        if ndim == 2:
            return (_normalize_body(data.tolist()),)
        if ndim == 3:
            return tuple(_normalize_body(body) for body in data.tolist())
        raise ValueError("TableResult data must be a 2D or 3D array-like value")
    if not _is_nested_sequence(data):
        raise ValueError("TableResult data must be a 2D or 3D array-like value")
    top = tuple(data)
    if not top:
        raise ValueError("TableResult data must contain at least one body or row")
    if all(_is_row_sequence(item) for item in top):
        return (_normalize_body(top),)
    if all(_is_nested_sequence(item) for item in top):
        return tuple(_normalize_body(item) for item in top)
    raise ValueError("TableResult data must be a 2D or 3D array-like value")


def _normalize_body(body: object) -> tuple[tuple[object, ...], ...]:
    if not _is_nested_sequence(body):
        raise ValueError("Each table body must be a 2D array-like value")
    rows = tuple(body)
    if not rows:
        raise ValueError("Each table body must contain at least one row")
    normalized_rows: list[tuple[object, ...]] = []
    expected_width: int | None = None
    for row in rows:
        if not _is_row_sequence(row):
            raise ValueError("Table body rows must be one-dimensional sequences of cell values")
        normalized_row = tuple(row)
        if not normalized_row:
            raise ValueError("Table body rows must contain at least one column")
        if expected_width is None:
            expected_width = len(normalized_row)
        elif len(normalized_row) != expected_width:
            raise ValueError("All rows in a table body must have the same logical width")
        normalized_rows.append(normalized_row)
    return tuple(normalized_rows)


def _is_nested_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _is_row_sequence(value: object) -> bool:
    if not _is_nested_sequence(value):
        return False
    return all(not _is_nested_sequence(cell) for cell in value)
