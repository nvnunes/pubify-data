from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .adapters import ArtifactWriter
from .discovery import PublicationDefinition
from .runtime import build_run_context, preload_loaders, run_figures, run_stats, run_tables


@dataclass(frozen=True)
class CoreCommandContext:
    """Inputs shared by reusable core command handlers."""

    publication: PublicationDefinition
    artifact_writer: ArtifactWriter | None = None
    loader_cache: dict[str, object] | None = None


CommandHandler = Callable[[CoreCommandContext, tuple[str, ...]], int]


@dataclass
class CommandRegistry:
    """Explicit command registry used by downstream CLIs."""

    handlers: dict[tuple[str, ...], CommandHandler] = field(default_factory=dict)

    def register(self, path: tuple[str, ...], handler: CommandHandler) -> None:
        if not path:
            raise ValueError("Command path must not be empty")
        if path in self.handlers:
            raise ValueError(f"Duplicate command registration: {' '.join(path)}")
        self.handlers[path] = handler

    def dispatch(self, context: CoreCommandContext, argv: tuple[str, ...]) -> int | None:
        for length in range(len(argv), 0, -1):
            key = argv[:length]
            handler = self.handlers.get(key)
            if handler is not None:
                return handler(context, argv[length:])
        return None


def register_core_commands(registry: CommandRegistry) -> None:
    """Register reusable neutral data/figure/stat/table list and update commands."""

    registry.register(("data", "list"), _list_data)
    registry.register(("figure", "list"), _list_figures)
    registry.register(("figure", "update"), _update_figures)
    registry.register(("stat", "list"), _list_stats)
    registry.register(("stat", "update"), _update_stats)
    registry.register(("table", "list"), _list_tables)
    registry.register(("table", "update"), _update_tables)
    registry.register(("update",), _update_all)


def _list_data(context: CoreCommandContext, args: tuple[str, ...]) -> int:
    _reject_args("data list", args)
    for loader_id in sorted(context.publication.loaders):
        print(loader_id)
    return 0


def _list_figures(context: CoreCommandContext, args: tuple[str, ...]) -> int:
    _reject_args("figure list", args)
    for figure_id in sorted(context.publication.figures):
        print(figure_id)
    return 0


def _list_stats(context: CoreCommandContext, args: tuple[str, ...]) -> int:
    _reject_args("stat list", args)
    for stat_id in sorted(context.publication.stats):
        print(stat_id)
    return 0


def _list_tables(context: CoreCommandContext, args: tuple[str, ...]) -> int:
    _reject_args("table list", args)
    for table_id in sorted(context.publication.tables):
        print(table_id)
    return 0


def _update_figures(context: CoreCommandContext, args: tuple[str, ...]) -> int:
    _reject_args("figure update", args)
    ctx = build_run_context(context.publication, loader_cache=context.loader_cache)
    preload_loaders(ctx, _loader_ids_for(context.publication.figures), include_nocache=True)
    results = run_figures(context.publication, ctx=ctx)
    _write(context, "figures", results)
    return 0


def _update_stats(context: CoreCommandContext, args: tuple[str, ...]) -> int:
    _reject_args("stat update", args)
    ctx = build_run_context(context.publication, loader_cache=context.loader_cache)
    preload_loaders(ctx, _loader_ids_for(context.publication.stats), include_nocache=True)
    _write(context, "stats", run_stats(context.publication, ctx=ctx))
    return 0


def _update_tables(context: CoreCommandContext, args: tuple[str, ...]) -> int:
    _reject_args("table update", args)
    ctx = build_run_context(context.publication, loader_cache=context.loader_cache)
    preload_loaders(ctx, _loader_ids_for(context.publication.tables), include_nocache=True)
    _write(context, "tables", run_tables(context.publication, ctx=ctx))
    return 0


def _update_all(context: CoreCommandContext, args: tuple[str, ...]) -> int:
    _reject_args("update", args)
    _update_figures(context, ())
    _update_stats(context, ())
    _update_tables(context, ())
    return 0


def _write(context: CoreCommandContext, group: str, results: object) -> None:
    writer = context.artifact_writer
    if writer is None:
        return
    method_name = f"write_{group}"
    write_method = getattr(writer, method_name, None)
    if not callable(write_method):
        raise TypeError(f"Artifact writer must implement {method_name}(results)")
    write_method(results)


def _loader_ids_for(specs: dict[str, object]) -> tuple[str, ...]:
    ordered: list[str] = []
    for spec in specs.values():
        for loader_id in spec.dependency_ids:
            if loader_id not in ordered:
                ordered.append(loader_id)
    return tuple(ordered)


def _reject_args(command: str, args: tuple[str, ...]) -> None:
    if args:
        raise ValueError(f"{command} does not accept additional arguments")
