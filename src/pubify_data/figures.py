from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FigurePanel:
    """One neutral figure panel payload plus renderer-specific metadata."""

    payload: object
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, init=False)
class BaseFigureResult:
    """Neutral logical figure result returned by a figure function."""

    panels: tuple[FigurePanel, ...]
    layout: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __init__(self, panels_or_panel: object | Sequence[object], *, layout: str | None = None, metadata: dict[str, object] | None = None) -> None:
        object.__setattr__(self, "panels", _normalize_panels(panels_or_panel))
        object.__setattr__(self, "layout", layout)
        object.__setattr__(self, "metadata", dict(metadata or {}))
        if layout is not None and not layout:
            raise ValueError("BaseFigureResult requires a non-empty layout when set")

    def panel(self, panel_number: int) -> object:
        """Return one panel payload using one-based panel numbering."""

        if panel_number < 1 or panel_number > len(self.panels):
            raise IndexError(f"Figure has {len(self.panels)} panel(s); requested panel {panel_number}")
        return self.panels[panel_number - 1].payload


def panel(payload: object, **metadata: object) -> FigurePanel:
    """Wrap one panel payload with renderer-specific metadata."""

    return FigurePanel(payload=payload, metadata=dict(metadata))


def normalize_figure_result(result: object) -> BaseFigureResult:
    """Normalize a supported figure return value into ``BaseFigureResult``."""

    if result is None:
        raise ValueError("Figure returned None")
    if isinstance(result, BaseFigureResult):
        return result
    return BaseFigureResult(result)


def _normalize_panels(value: object | Sequence[object]) -> tuple[FigurePanel, ...]:
    if isinstance(value, FigurePanel):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = tuple(value)
        if not items:
            raise ValueError("BaseFigureResult requires at least one panel")
        return tuple(item if isinstance(item, FigurePanel) else FigurePanel(item) for item in items)
    return (FigurePanel(value),)
