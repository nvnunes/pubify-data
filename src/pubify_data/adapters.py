from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class WorkspaceAdapter:
    """Downstream-owned workspace context supplied to ``pubify-data``.

    ``pubify-data`` treats the workspace as opaque context. Downstream packages
    own root names, config schemas, and executable behavior; this adapter only
    records the resolved workspace root and optional raw config object that a
    downstream package wants to carry through its own lifecycle.
    """

    workspace_root: Path
    config: object | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace_root", Path(self.workspace_root).expanduser().resolve())


@dataclass(frozen=True)
class PublicationAdapter:
    """Resolved downstream publication paths used by the neutral runtime.

    Downstream packages must resolve their own workspace schemas before calling
    into ``pubify-data``. The runtime needs only the publication id, import
    entrypoint, publication root, local data root, and named external data
    roots.
    """

    publication_id: str
    entrypoint: Path
    data_root: Path
    publication_root: Path | None = None
    external_data_roots: Mapping[str, Path | str] = field(default_factory=dict)
    workspace: WorkspaceAdapter | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.publication_id, str) or not self.publication_id:
            raise ValueError("PublicationAdapter requires a non-empty publication_id")
        entrypoint = Path(self.entrypoint).expanduser()
        publication_root = Path(self.publication_root).expanduser() if self.publication_root is not None else entrypoint.parent
        data_root = Path(self.data_root).expanduser()
        external_data_roots = _normalize_external_roots(self.external_data_roots)
        object.__setattr__(self, "entrypoint", entrypoint)
        object.__setattr__(self, "publication_root", publication_root)
        object.__setattr__(self, "data_root", data_root)
        object.__setattr__(self, "external_data_roots", external_data_roots)


class ArtifactWriter(Protocol):
    """Optional downstream persistence hooks for neutral computed artifacts."""

    def write_figures(self, results: object) -> None:
        """Persist neutral figure results."""

    def write_stats(self, results: object) -> None:
        """Persist neutral stat results."""

    def write_tables(self, results: object) -> None:
        """Persist neutral table results."""


def publication_adapter_from_legacy(
    publication_id: str,
    entrypoint: Path,
    *,
    paths: object,
    config: object,
) -> PublicationAdapter:
    """Build a ``PublicationAdapter`` from the transitional loose objects."""

    data_root = getattr(paths, "data_root", None)
    if data_root is None:
        raise ValueError("Legacy publication paths object must provide data_root")
    return PublicationAdapter(
        publication_id=publication_id,
        entrypoint=entrypoint,
        data_root=Path(data_root),
        external_data_roots=getattr(config, "external_data_roots", {}),
    )


def _normalize_external_roots(external_data_roots: Mapping[str, Path | str]) -> dict[str, Path]:
    normalized: dict[str, Path] = {}
    for name, root in external_data_roots.items():
        if not isinstance(name, str) or not name:
            raise ValueError("External data root names must be non-empty strings")
        normalized[name] = Path(root).expanduser()
    return normalized
