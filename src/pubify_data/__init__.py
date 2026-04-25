"""TeX-agnostic publication data and artifact runtime."""

from .adapters import ArtifactWriter, PublicationAdapter, WorkspaceAdapter
from .cli import CommandRegistry, CoreCommandContext, register_core_commands
from .config import PubifyConfig, find_workspace_root, load_config_section, load_pubify_config
from .data import (
    artifact_namespace_path,
    artifact_namespace_root,
    load_publication_data_npz,
    publication_data_path,
    save_publication_data_npz,
)
from .decorators import data, external_data, figure, stat, table
from .discovery import (
    FigureSpec,
    LoaderSpec,
    PublicationDefinition,
    StatSpec,
    TableSpec,
    discover_publication,
    load_publication_from_entrypoint,
)
from .figures import BaseFigureResult, FigurePanel, panel
from .runtime import (
    RunContext,
    UserCodeExecutionError,
    build_run_context,
    figure_ids,
    resolve_loader,
    run_figures,
    run_stats,
    run_tables,
    stat_ids,
    table_ids,
    validate_dependencies,
)
from .stats import BaseStatResult, ComputedStat, StatValue
from .tables import BaseTableResult, ComputedTable

__all__ = [
    "ArtifactWriter",
    "CommandRegistry",
    "ComputedStat",
    "ComputedTable",
    "CoreCommandContext",
    "BaseFigureResult",
    "BaseStatResult",
    "BaseTableResult",
    "FigurePanel",
    "FigureSpec",
    "LoaderSpec",
    "PublicationAdapter",
    "PublicationDefinition",
    "PubifyConfig",
    "RunContext",
    "StatSpec",
    "StatValue",
    "TableSpec",
    "UserCodeExecutionError",
    "WorkspaceAdapter",
    "artifact_namespace_path",
    "artifact_namespace_root",
    "build_run_context",
    "data",
    "discover_publication",
    "external_data",
    "figure",
    "figure_ids",
    "find_workspace_root",
    "load_config_section",
    "load_publication_data_npz",
    "load_publication_from_entrypoint",
    "load_pubify_config",
    "panel",
    "publication_data_path",
    "register_core_commands",
    "resolve_loader",
    "run_figures",
    "run_stats",
    "run_tables",
    "save_publication_data_npz",
    "stat",
    "stat_ids",
    "table",
    "table_ids",
    "validate_dependencies",
]
