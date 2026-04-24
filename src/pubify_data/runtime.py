from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
import io
from pathlib import Path
import traceback

from .discovery import PublicationDefinition
from .figures import FigureResult, normalize_figure_result
from .stats import ComputedStat, compute_stat
from .tables import ComputedTable, compute_table


@dataclass
class RunContext:
    """Runtime state shared while resolving loaders and computed artifacts."""

    publication: PublicationDefinition
    loader_cache: dict[str, object] = field(default_factory=dict)
    command_loader_cache: dict[str, object] = field(default_factory=dict)
    updated_loader_ids: set[str] = field(default_factory=set)
    captured_data_output: dict[str, list[str]] = field(default_factory=dict)
    captured_output: dict[str, list[str]] = field(default_factory=lambda: {"figure": [], "stat": [], "table": []})
    rc: object | None = None


class UserCodeExecutionError(RuntimeError):
    """Raised when publication-defined Python code fails during execution."""

    def __init__(self, lines: list[str]) -> None:
        self.lines = tuple(lines)
        super().__init__(lines[-1] if lines else "Publication code execution failed")


def build_run_context(publication: PublicationDefinition, *, loader_cache: dict[str, object] | None = None, rc: object | None = None) -> RunContext:
    """Create one command-scoped runtime context for a publication."""

    return RunContext(publication=publication, loader_cache=loader_cache if loader_cache is not None else {}, rc=rc)


def preload_loaders(ctx: RunContext, loader_ids: tuple[str, ...], *, include_nocache: bool) -> None:
    """Resolve selected loaders into ``ctx`` before artifacts run."""

    for loader_id in loader_ids:
        loader = ctx.publication.loaders[loader_id]
        if loader.nocache and not include_nocache:
            continue
        resolve_loader(ctx, loader_id)


def resolve_loader(ctx: RunContext, loader_id: str) -> object:
    """Resolve one loader and return its computed value."""

    loader = ctx.publication.loaders[loader_id]
    if loader.nocache:
        if loader_id in ctx.command_loader_cache:
            return ctx.command_loader_cache[loader_id]
    elif loader_id in ctx.loader_cache:
        return ctx.loader_cache[loader_id]
    root = _loader_root(ctx.publication, loader)
    if loader.style == "single":
        relative_path = next(iter(loader.relative_paths.values()))
        resolved = _capture_loader_output(ctx, loader_id, loader.func, ctx, _resolve_loader_path(root, relative_path, loader_id))
    elif loader.style == "named":
        resolved = _capture_loader_output(
            ctx,
            loader_id,
            loader.func,
            ctx,
            **{name: _resolve_loader_path(root, relative_path, loader_id) for name, relative_path in loader.relative_paths.items()},
        )
    else:
        raise ValueError(f"Unsupported loader style '{loader.style}'")
    if loader.nocache:
        ctx.command_loader_cache[loader_id] = resolved
    else:
        ctx.loader_cache[loader_id] = resolved
    ctx.updated_loader_ids.add(loader_id)
    return resolved


def run_figures(publication: PublicationDefinition, figure_id: str | None = None, ctx: RunContext | None = None) -> tuple[tuple[str, FigureResult], ...]:
    """Run one or more figure functions and return neutral figure results."""

    run_ctx = ctx or build_run_context(publication)
    figure_ids = [figure_id] if figure_id is not None else sorted(publication.figures)
    computed: list[tuple[str, FigureResult]] = []
    for current_id in figure_ids:
        if current_id not in publication.figures:
            raise KeyError(f"Unknown figure '{current_id}'")
        spec = publication.figures[current_id]
        resolved_args = [resolve_loader(run_ctx, dep_id) for dep_id in spec.dependency_ids]
        computed.append((current_id, normalize_figure_result(_capture_dynamic_output(run_ctx, "figure", spec.func, run_ctx, *resolved_args))))
    return tuple(computed)


def run_stats(publication: PublicationDefinition, stat_id: str | None = None, ctx: RunContext | None = None) -> tuple[ComputedStat, ...]:
    """Run one or more stat functions and return neutral computed stats."""

    run_ctx = ctx or build_run_context(publication)
    stat_ids = [stat_id] if stat_id is not None else sorted(publication.stats)
    computed: list[ComputedStat] = []
    for current_id in stat_ids:
        if current_id not in publication.stats:
            raise KeyError(f"Unknown stat '{current_id}'")
        spec = publication.stats[current_id]
        resolved_args = [resolve_loader(run_ctx, dep_id) for dep_id in spec.dependency_ids]
        computed.append(compute_stat(current_id, _capture_dynamic_output(run_ctx, "stat", spec.func, run_ctx, *resolved_args)))
    return tuple(computed)


def run_tables(publication: PublicationDefinition, table_id: str | None = None, ctx: RunContext | None = None) -> tuple[ComputedTable, ...]:
    """Run one or more table functions and return neutral computed tables."""

    run_ctx = ctx or build_run_context(publication)
    table_ids = [table_id] if table_id is not None else sorted(publication.tables)
    computed: list[ComputedTable] = []
    for current_id in table_ids:
        if current_id not in publication.tables:
            raise KeyError(f"Unknown table '{current_id}'")
        spec = publication.tables[current_id]
        resolved_args = [resolve_loader(run_ctx, dep_id) for dep_id in spec.dependency_ids]
        computed.append(compute_table(current_id, _capture_dynamic_output(run_ctx, "table", spec.func, run_ctx, *resolved_args)))
    return tuple(computed)


def validate_dependencies(publication: PublicationDefinition) -> list[str]:
    """Return dependency errors without running user code."""

    errors: list[str] = []
    for figure in publication.figures.values():
        for dep in figure.dependency_ids:
            if dep not in publication.loaders:
                errors.append(f"Figure '{figure.figure_id}' depends on unknown loader '{dep}'")
    for stat in publication.stats.values():
        for dep in stat.dependency_ids:
            if dep not in publication.loaders:
                errors.append(f"Stat '{stat.stat_id}' depends on unknown loader '{dep}'")
    for table in publication.tables.values():
        for dep in table.dependency_ids:
            if dep not in publication.loaders:
                errors.append(f"Table '{table.table_id}' depends on unknown loader '{dep}'")
    return errors


def _loader_root(publication: PublicationDefinition, loader: object) -> Path:
    if loader.kind == "data":
        return publication.data_root
    if loader.kind == "external_data":
        if loader.root_name is None:
            raise ValueError(f"Loader '{loader.loader_id}' is missing external data root metadata")
        external_roots = publication.external_data_roots
        if loader.root_name not in external_roots:
            raise ValueError(f"Loader '{loader.loader_id}' references undefined external data root '{loader.root_name}'")
        return external_roots[loader.root_name]
    raise ValueError(f"Unsupported loader kind '{loader.kind}'")


def _resolve_loader_path(root: Path, relative_path: str, loader_id: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"Loader '{loader_id}' path must be relative, not absolute: {relative_path}")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"Loader '{loader_id}' path must stay under its configured root: {relative_path}")
    return root / candidate


def _capture_loader_output(ctx: RunContext, loader_id: str, func: object, *args: object, **kwargs: object) -> object:
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer), redirect_stderr(buffer):
            return func(*args, **kwargs)
    except Exception as exc:
        output_lines = buffer.getvalue().splitlines()
        detail_lines = [f"Loader '{loader_id}' failed: {exc}", *output_lines, *traceback.format_exception_only(type(exc), exc)]
        raise UserCodeExecutionError(detail_lines) from exc
    finally:
        lines = buffer.getvalue().splitlines()
        if lines:
            ctx.captured_data_output.setdefault(loader_id, []).extend(lines)


def _capture_dynamic_output(ctx: RunContext, group: str, func: object, *args: object, **kwargs: object) -> object:
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer), redirect_stderr(buffer):
            return func(*args, **kwargs)
    except Exception as exc:
        output_lines = buffer.getvalue().splitlines()
        detail_lines = [f"{group.title()} '{getattr(func, '__name__', '<callable>')}' failed: {exc}", *output_lines, *traceback.format_exception_only(type(exc), exc)]
        raise UserCodeExecutionError(detail_lines) from exc
    finally:
        lines = buffer.getvalue().splitlines()
        if lines:
            ctx.captured_output.setdefault(group, []).extend(lines)
