from __future__ import annotations

from dataclasses import dataclass
from importlib import invalidate_caches
from importlib.util import module_from_spec, spec_from_file_location
import inspect
from pathlib import Path
import sys
from types import ModuleType

from .adapters import PublicationAdapter, publication_adapter_from_legacy


@dataclass(frozen=True)
class LoaderSpec:
    loader_id: str
    func: object
    kind: str
    root_name: str | None
    style: str
    relative_paths: dict[str, str]
    nocache: bool


@dataclass(frozen=True)
class FigureSpec:
    figure_id: str
    func: object
    dependency_ids: tuple[str, ...]


@dataclass(frozen=True)
class StatSpec:
    stat_id: str
    func: object
    dependency_ids: tuple[str, ...]


@dataclass(frozen=True)
class TableSpec:
    table_id: str
    func: object
    dependency_ids: tuple[str, ...]


@dataclass(frozen=True)
class PublicationDefinition:
    publication_id: str
    adapter: PublicationAdapter
    module: ModuleType
    loaders: dict[str, LoaderSpec]
    figures: dict[str, FigureSpec]
    stats: dict[str, StatSpec]
    tables: dict[str, TableSpec]

    @property
    def publication_root(self) -> Path:
        return self.adapter.publication_root

    @property
    def entrypoint(self) -> Path:
        return self.adapter.entrypoint

    @property
    def data_root(self) -> Path:
        return self.adapter.data_root

    @property
    def external_data_roots(self) -> dict[str, Path]:
        return dict(self.adapter.external_data_roots)


def load_publication_from_entrypoint(
    publication_id: str,
    entrypoint: Path | None = None,
    *,
    adapter: PublicationAdapter | None = None,
    paths: object | None = None,
    config: object | None = None,
) -> PublicationDefinition:
    """Import one downstream-supplied entrypoint and discover decorated objects."""

    publication_adapter = _resolve_publication_adapter(publication_id, entrypoint, adapter=adapter, paths=paths, config=config)
    if not publication_adapter.entrypoint.exists():
        raise FileNotFoundError(f"Missing publication entrypoint: {publication_adapter.entrypoint}")
    module = _import_publication_module(publication_adapter)
    return discover_publication(publication_adapter.publication_id, module, adapter=publication_adapter)


def discover_publication(
    publication_id: str,
    module: ModuleType,
    *,
    adapter: PublicationAdapter,
) -> PublicationDefinition:
    """Discover decorated loaders, figures, stats, and tables from an imported module."""

    if publication_id != adapter.publication_id:
        raise ValueError("Publication id must match the supplied PublicationAdapter")
    return PublicationDefinition(
        publication_id=publication_id,
        adapter=adapter,
        module=module,
        loaders=_discover_loaders(module),
        figures=_discover_figures(module),
        stats=_discover_stats(module),
        tables=_discover_tables(module),
    )


def _resolve_publication_adapter(
    publication_id: str,
    entrypoint: Path | None,
    *,
    adapter: PublicationAdapter | None,
    paths: object | None,
    config: object | None,
) -> PublicationAdapter:
    if adapter is not None:
        if entrypoint is not None and Path(entrypoint) != adapter.entrypoint:
            raise ValueError("Pass either entrypoint or PublicationAdapter.entrypoint, not conflicting values")
        if publication_id != adapter.publication_id:
            raise ValueError("Publication id must match the supplied PublicationAdapter")
        return adapter
    if entrypoint is None:
        raise ValueError("load_publication_from_entrypoint requires an entrypoint or adapter")
    if paths is None or config is None:
        raise ValueError("Transitional entrypoint loading requires paths and config when adapter is not supplied")
    return publication_adapter_from_legacy(publication_id, entrypoint, paths=paths, config=config)


def _import_publication_module(adapter: PublicationAdapter) -> ModuleType:
    module_name = f"pubify_data_publication_{adapter.publication_id}"
    publication_root = adapter.publication_root
    _purge_publication_modules(publication_root)
    invalidate_caches()
    publication_root_str = str(publication_root)
    added_path = False
    if publication_root_str not in sys.path:
        sys.path.insert(0, publication_root_str)
        added_path = True
    spec = spec_from_file_location(module_name, adapter.entrypoint)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not build import spec for {adapter.entrypoint}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
        if added_path and sys.path and sys.path[0] == publication_root_str:
            sys.path.pop(0)
    return module


def _purge_publication_modules(publication_root: Path) -> None:
    resolved_root = publication_root.resolve()
    for module_name, module in list(sys.modules.items()):
        if _module_lives_under_root(module, resolved_root):
            sys.modules.pop(module_name, None)


def _module_lives_under_root(module: object, root: Path) -> bool:
    module_file = getattr(module, "__file__", None)
    if module_file is not None and _path_lives_under_root(module_file, root):
        return True
    module_paths = getattr(module, "__path__", None)
    if module_paths is None:
        return False
    try:
        return any(_path_lives_under_root(path, root) for path in module_paths)
    except TypeError:
        return False


def _path_lives_under_root(path_like: str | Path, root: Path) -> bool:
    try:
        resolved_path = Path(path_like).resolve()
    except OSError:
        return False
    return resolved_path == root or root in resolved_path.parents


def _discover_loaders(module: ModuleType) -> dict[str, LoaderSpec]:
    loaders: dict[str, LoaderSpec] = {}
    for _, member in module.__dict__.items():
        metadata = getattr(member, "__pubify_data_loader__", None)
        if metadata is None:
            metadata = getattr(member, "__pubs_loader__", None)
        if metadata is None:
            continue
        loader_id = _strip_prefix(member.__name__, "load_")
        if loader_id in loaders:
            raise ValueError(f"Duplicate loader id '{loader_id}'")
        metadata_paths = dict(metadata["paths"])
        _validate_loader_signature(loader_id, member, metadata["style"], metadata_paths)
        loaders[loader_id] = LoaderSpec(
            loader_id=loader_id,
            func=member,
            kind=metadata["kind"],
            root_name=metadata.get("root_name"),
            style=metadata["style"],
            relative_paths=metadata_paths,
            nocache=bool(metadata["nocache"]),
        )
    return loaders


def _discover_figures(module: ModuleType) -> dict[str, FigureSpec]:
    figures: dict[str, FigureSpec] = {}
    for _, member in inspect.getmembers(module):
        if not getattr(member, "__pubify_data_figure__", False) and not getattr(member, "__pubs_figure__", False):
            continue
        figure_id = _strip_prefix(member.__name__, "plot_")
        if figure_id in figures:
            raise ValueError(f"Duplicate figure id '{figure_id}'")
        figures[figure_id] = FigureSpec(figure_id, member, _dependency_ids(member, kind="Figure"))
    return figures


def _discover_stats(module: ModuleType) -> dict[str, StatSpec]:
    stats: dict[str, StatSpec] = {}
    for _, member in inspect.getmembers(module):
        if not getattr(member, "__pubify_data_stat__", False) and not getattr(member, "__pubs_stat__", False):
            continue
        stat_id = _strip_prefix(member.__name__, "compute_")
        if stat_id in stats:
            raise ValueError(f"Duplicate stat id '{stat_id}'")
        stats[stat_id] = StatSpec(stat_id, member, _dependency_ids(member, kind="Stat"))
    return stats


def _discover_tables(module: ModuleType) -> dict[str, TableSpec]:
    tables: dict[str, TableSpec] = {}
    for _, member in inspect.getmembers(module):
        if not getattr(member, "__pubify_data_table__", False) and not getattr(member, "__pubs_table__", False):
            continue
        table_id = _strip_prefix(member.__name__, "tabulate_")
        if table_id in tables:
            raise ValueError(f"Duplicate table id '{table_id}'")
        tables[table_id] = TableSpec(table_id, member, _dependency_ids(member, kind="Table"))
    return tables


def _validate_loader_signature(loader_id: str, func: object, style: str, paths: dict[str, str]) -> None:
    params = tuple(inspect.signature(func).parameters.values())
    if not params or params[0].name != "ctx":
        raise ValueError(f"Loader '{func.__name__}' must accept ctx as its first parameter")
    resolved_params = params[1:]
    if style == "single":
        if len(resolved_params) != 1:
            raise ValueError(f"Loader '{loader_id}' must accept exactly one resolved path parameter after ctx")
        return
    if style == "named":
        expected_names = tuple(paths)
        param_names = tuple(param.name for param in resolved_params)
        if param_names != expected_names:
            raise ValueError(f"Loader '{loader_id}' must accept named path parameters {expected_names} after ctx")
        return
    raise ValueError(f"Unsupported loader style for loader '{loader_id}': {style}")


def _dependency_ids(func: object, *, kind: str) -> tuple[str, ...]:
    params = tuple(inspect.signature(func).parameters.values())
    if not params or params[0].name != "ctx":
        raise ValueError(f"{kind} '{func.__name__}' must accept ctx as its first parameter")
    return tuple(param.name for param in params[1:])


def _strip_prefix(name: str, prefix: str) -> str:
    return name[len(prefix):] if name.startswith(prefix) else name
