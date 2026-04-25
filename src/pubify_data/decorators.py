from __future__ import annotations

from collections.abc import Callable
from pathlib import Path


def figure(func: Callable) -> Callable:
    """Mark a callable as a computed figure entrypoint."""

    setattr(func, "__pubify_data_figure__", True)
    return func


def stat(func: Callable) -> Callable:
    """Mark a callable as a computed stat entrypoint."""

    setattr(func, "__pubify_data_stat__", True)
    return func


def table(func: Callable) -> Callable:
    """Mark a callable as a computed table entrypoint."""

    setattr(func, "__pubify_data_table__", True)
    return func


def data(*args: str, nocache: bool = False, **paths: str) -> Callable[[Callable], Callable]:
    """Declare a loader that reads pinned publication-local data."""

    metadata = _loader_metadata("data", None, "@data", args, paths, nocache=nocache)
    def decorate(func: Callable) -> Callable:
        setattr(func, "__pubify_data_loader__", metadata)
        return func
    return decorate


def external_data(root_name: str, *args: str, nocache: bool = False, **paths: str) -> Callable[[Callable], Callable]:
    """Declare a loader that reads from a downstream-configured external data root."""

    if not isinstance(root_name, str) or not root_name:
        raise ValueError("@external_data requires a non-empty root name")
    metadata = _loader_metadata("external_data", root_name, "@external_data", args, paths, nocache=nocache)
    def decorate(func: Callable) -> Callable:
        setattr(func, "__pubify_data_loader__", metadata)
        return func
    return decorate


def _loader_metadata(
    kind: str,
    root_name: str | None,
    decorator_name: str,
    args: tuple[str, ...],
    paths: dict[str, str],
    *,
    nocache: bool,
) -> dict[str, object]:
    if args and paths:
        raise ValueError(f"{decorator_name} accepts either one positional path or named paths, not both")
    if not args and not paths:
        raise ValueError(f"{decorator_name} requires exactly one positional path or one-or-more named paths")
    if len(args) > 1:
        raise ValueError(f"{decorator_name} accepts at most one positional path")
    if args:
        style = "single"
        resolved_paths = {"path": _validate_loader_relative_path(args[0], decorator_name=decorator_name)}
    else:
        style = "named"
        resolved_paths = {
            name: _validate_loader_relative_path(value, decorator_name=decorator_name)
            for name, value in paths.items()
        }
    metadata: dict[str, object] = {
        "kind": kind,
        "style": style,
        "paths": resolved_paths,
        "nocache": nocache,
    }
    if root_name is not None:
        metadata["root_name"] = root_name
    return metadata


def _validate_loader_relative_path(value: str, *, decorator_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{decorator_name} paths must be non-empty relative paths")
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"{decorator_name} paths must be relative, not absolute: {value}")
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{decorator_name} paths must stay under their configured root: {value}")
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise ValueError(f"{decorator_name} paths must be non-empty relative paths")
    return normalized
