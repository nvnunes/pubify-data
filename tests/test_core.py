from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from pubify_data import (
    BaseFigureResult,
    BaseStatResult,
    BaseTableResult,
    CommandRegistry,
    CoreCommandContext,
    PublicationAdapter,
    UserCodeExecutionError,
    artifact_namespace_path,
    artifact_namespace_root,
    build_run_context,
    data,
    figure,
    load_publication_from_entrypoint,
    register_core_commands,
    run_figures,
    run_stats,
    run_tables,
    stat,
    stat_ids,
    table,
    validate_dependencies,
)
from pubify_data.config import load_config_section, load_pubify_config
from pubify_data.data import load_publication_data_npz, save_publication_data_npz


@dataclass(frozen=True)
class Paths:
    data_root: Path


@dataclass(frozen=True)
class Config:
    external_data_roots: dict[str, str]


def test_config_loads_namespaced_sections(tmp_path: Path) -> None:
    (tmp_path / "pubify.yaml").write_text("pubify-pubs:\n  publications_root: papers\n", encoding="utf-8")

    loaded = load_pubify_config(tmp_path)

    assert loaded.section("pubify-pubs") == {"publications_root": "papers"}
    assert load_config_section(tmp_path, "missing") == {}


def test_artifact_namespace_helpers_resolve_under_supplied_data_root(tmp_path: Path) -> None:
    data_root = tmp_path / "paper" / "data"

    namespace_root = artifact_namespace_root(data_root, "derived/artifacts", create=True)
    artifact_path = artifact_namespace_path(data_root, "derived/artifacts", "figures/example.pdf", create_parent=True)

    assert namespace_root == data_root / "derived" / "artifacts"
    assert namespace_root.exists()
    assert artifact_path == data_root / "derived" / "artifacts" / "figures" / "example.pdf"
    assert artifact_path.parent.exists()


def test_artifact_namespace_helpers_reject_paths_outside_data_root(tmp_path: Path) -> None:
    data_root = tmp_path / "data"

    with pytest.raises(ValueError, match="must be relative, not absolute"):
        artifact_namespace_root(data_root, "/absolute")
    with pytest.raises(ValueError, match="must stay under the publication data root"):
        artifact_namespace_root(data_root, "../outside")
    with pytest.raises(ValueError, match="must be a non-empty relative path"):
        artifact_namespace_root(data_root, "")
    with pytest.raises(ValueError, match="must be a non-empty relative path"):
        artifact_namespace_root(data_root, ".")
    with pytest.raises(ValueError, match="must be relative, not absolute"):
        artifact_namespace_path(data_root, "artifacts", "/absolute")
    with pytest.raises(ValueError, match="must stay under the publication data root"):
        artifact_namespace_path(data_root, "artifacts", "../outside")
    with pytest.raises(ValueError, match="must be a non-empty relative path"):
        artifact_namespace_path(data_root, "artifacts", "")


def test_decorators_and_runtime_execute_loader_dependencies(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "sample.txt").write_text("value", encoding="utf-8")
    entrypoint = tmp_path / "figures.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import data, figure, stat",
            "@data('sample.txt')",
            "def load_sample(ctx, path):",
            "    return path.read_text(encoding='utf-8')",
            "@figure",
            "def plot_demo(ctx, sample):",
            "    return sample",
            "@stat",
            "def compute_demo(ctx, sample):",
            "    return {'value': sample}",
        ]) + "\n",
        encoding="utf-8",
    )
    publication = load_publication_from_entrypoint("demo", entrypoint, paths=Paths(data_root), config=Config({}))

    assert run_figures(publication)[0][1].panels[0].payload == "value"
    assert run_stats(publication)[0].values[0].value == "value"


def test_base_result_types_normalize_figures_stats_and_tables(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    entrypoint = tmp_path / "figures.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import BaseFigureResult, BaseStatResult, BaseTableResult, figure, stat, table",
            "@figure",
            "def plot_demo(ctx):",
            "    return BaseFigureResult(['left', 'right'], layout='two', metadata={'caption_lines': 2})",
            "@stat",
            "def compute_demo(ctx):",
            "    return BaseStatResult({'mean': '42'}, metadata={'format': 'text'})",
            "@table",
            "def tabulate_demo(ctx):",
            "    return BaseTableResult([['A', 'B']], metadata={'formats': ('{}', '{}')})",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter("demo", entrypoint=entrypoint, data_root=data_root)
    publication = load_publication_from_entrypoint("demo", adapter=adapter)

    figure_result = run_figures(publication)[0][1]
    stat_result = run_stats(publication)[0]
    table_result = run_tables(publication)[0]

    assert isinstance(figure_result, BaseFigureResult)
    assert figure_result.layout == "two"
    assert [panel.payload for panel in figure_result.panels] == ["left", "right"]
    assert stat_result.values[0].key == "mean"
    assert stat_result.values[0].value == "42"
    assert table_result.bodies == ((("A", "B"),),)
    assert table_result.metadata == {"formats": ("{}", "{}")}


def test_source_publications_are_reused_through_local_wrapper_code(tmp_path: Path) -> None:
    source_root = tmp_path / "papers" / "ao4elt8"
    source_data = source_root / "custom-data"
    source_data.mkdir(parents=True)
    (source_data / "value.txt").write_text("source", encoding="utf-8")
    source_entrypoint = source_root / "entry.py"
    source_entrypoint.write_text(
        "\n".join([
            "from pubify_data import data, figure, stat",
            "@data('value.txt')",
            "def load_value(ctx, path):",
            "    return path.read_text(encoding='utf-8')",
            "@figure",
            "def plot_map(ctx, value):",
            "    return ['first', value]",
            "@stat",
            "def compute_summary(ctx, value):",
            "    return {'value': value}",
        ]) + "\n",
        encoding="utf-8",
    )
    presentation_root = tmp_path / "slides" / "talk"
    presentation_data = presentation_root / "data"
    presentation_data.mkdir(parents=True)
    entrypoint = presentation_root / "figures.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import figure, stat",
            "@figure",
            "def plot_local(ctx):",
            "    return 'local'",
            "@figure",
            "def plot_reused(ctx):",
            "    return ctx.source('ao4elt8').figure('map').panel(2)",
            "@stat",
            "def compute_reused(ctx):",
            "    return ctx.source('ao4elt8').stat('summary')",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter(
        "talk",
        entrypoint=entrypoint,
        publication_root=presentation_root,
        data_root=presentation_data,
        source_adapters={
            "ao4elt8": PublicationAdapter(
                "ao4elt8",
                publication_root=source_root,
                entrypoint=source_entrypoint,
                data_root=source_data,
            ),
        },
    )
    publication = load_publication_from_entrypoint("talk", adapter=adapter)

    assert [artifact_id for artifact_id, _ in run_figures(publication)] == ["local", "reused"]
    assert run_figures(publication, "reused")[0][1].panels[0].payload == "source"
    with pytest.raises(KeyError, match="Unknown figure"):
        run_figures(publication, "ao4elt8.map")
    assert stat_ids(publication) == ("reused",)
    assert run_stats(publication, "reused")[0].values[0].value == "source"


def test_publication_adapter_supports_custom_downstream_root_layout(tmp_path: Path) -> None:
    publication_root = tmp_path / "sources" / "paper-a"
    data_root = tmp_path / "outputs" / "paper-data" / "paper-a"
    external_root = tmp_path / "inputs" / "raw"
    publication_root.mkdir(parents=True)
    data_root.mkdir(parents=True)
    external_root.mkdir(parents=True)
    (data_root / "local.txt").write_text("local", encoding="utf-8")
    (external_root / "raw.txt").write_text("external", encoding="utf-8")
    entrypoint = publication_root / "entrypoint.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import data, external_data, stat",
            "@data('local.txt')",
            "def load_local(ctx, path):",
            "    return path.read_text(encoding='utf-8')",
            "@external_data('raw', 'raw.txt')",
            "def load_raw(ctx, path):",
            "    return path.read_text(encoding='utf-8')",
            "@stat",
            "def compute_combined(ctx, local, raw):",
            "    return {'combined': f'{local}:{raw}'}",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter(
        publication_id="paper-a",
        entrypoint=entrypoint,
        publication_root=publication_root,
        data_root=data_root,
        external_data_roots={"raw": external_root},
    )

    publication = load_publication_from_entrypoint("paper-a", adapter=adapter)

    assert run_stats(publication)[0].values[0].value == "local:external"


def test_validate_dependencies_reports_missing_loaders(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    entrypoint = tmp_path / "figures.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import figure",
            "@figure",
            "def plot_demo(ctx, missing):",
            "    return missing",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter("demo", entrypoint=entrypoint, data_root=data_root)
    publication = load_publication_from_entrypoint("demo", adapter=adapter)

    assert validate_dependencies(publication) == ["Figure 'demo' depends on unknown loader 'missing'"]


def test_validate_dependencies_reports_undefined_external_data_roots(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    entrypoint = tmp_path / "figures.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import external_data, stat",
            "@external_data('missing', 'sample.txt')",
            "def load_sample(ctx, path):",
            "    return path.read_text(encoding='utf-8')",
            "@stat",
            "def compute_demo(ctx, sample):",
            "    return sample",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter("demo", entrypoint=entrypoint, data_root=data_root)
    publication = load_publication_from_entrypoint("demo", adapter=adapter)

    assert validate_dependencies(publication) == ["Loader 'sample' references undefined external data root 'missing'"]


def test_discovery_ignores_legacy_pubs_marker_names(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    entrypoint = tmp_path / "figures.py"
    entrypoint.write_text(
        "\n".join([
            "def plot_legacy(ctx):",
            "    return 'legacy'",
            "plot_legacy.__pubs_figure__ = True",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter("demo", entrypoint=entrypoint, data_root=data_root)
    publication = load_publication_from_entrypoint("demo", adapter=adapter)

    assert publication.figures == {}


def test_loader_cache_can_be_shared_across_run_contexts(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "sample.txt").write_text("cached", encoding="utf-8")
    entrypoint = tmp_path / "stats.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import data, stat",
            "CALLS = 0",
            "@data('sample.txt')",
            "def load_sample(ctx, path):",
            "    global CALLS",
            "    CALLS += 1",
            "    return path.read_text(encoding='utf-8')",
            "@stat",
            "def compute_first(ctx, sample):",
            "    return sample",
            "@stat",
            "def compute_second(ctx, sample):",
            "    return sample.upper()",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter("demo", entrypoint=entrypoint, data_root=data_root)
    publication = load_publication_from_entrypoint("demo", adapter=adapter)
    shared_cache: dict[str, object] = {}

    run_stats(publication, ctx=build_run_context(publication, loader_cache=shared_cache))
    run_stats(publication, ctx=build_run_context(publication, loader_cache=shared_cache))

    assert publication.module.CALLS == 1
    assert shared_cache == {"sample": "cached"}


def test_user_code_errors_include_captured_output(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "sample.txt").write_text("value", encoding="utf-8")
    entrypoint = tmp_path / "figures.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import data, figure",
            "@data('sample.txt')",
            "def load_sample(ctx, path):",
            "    print('loader before failure')",
            "    raise RuntimeError('broken loader')",
            "@figure",
            "def plot_demo(ctx, sample):",
            "    return sample",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter("demo", entrypoint=entrypoint, data_root=data_root)
    publication = load_publication_from_entrypoint("demo", adapter=adapter)

    with pytest.raises(UserCodeExecutionError) as exc_info:
        run_figures(publication)

    assert "Loader 'sample' failed: broken loader" in exc_info.value.lines
    assert "loader before failure" in exc_info.value.lines


def test_loader_tuple_return_is_user_code_error(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "sample.txt").write_text("value", encoding="utf-8")
    entrypoint = tmp_path / "figures.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import data, figure",
            "@data('sample.txt')",
            "def load_sample(ctx, path):",
            "    return ('a', 'b')",
            "@figure",
            "def plot_demo(ctx, sample):",
            "    return sample",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter("demo", entrypoint=entrypoint, data_root=data_root)
    publication = load_publication_from_entrypoint("demo", adapter=adapter)

    with pytest.raises(UserCodeExecutionError) as exc_info:
        run_figures(publication)

    assert "Loader 'sample' returned a tuple." in str(exc_info.value)


def test_tables_accept_downstream_table_like_result_with_metadata(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    entrypoint = tmp_path / "tables.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import table",
            "class DownstreamTable:",
            "    bodies = (((1, 2),),)",
            "    width = 2",
            "    metadata = {'formats': ('{:.1f}', '{}')}",
            "@table",
            "def tabulate_demo(ctx):",
            "    return DownstreamTable()",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter("demo", entrypoint=entrypoint, data_root=data_root)
    publication = load_publication_from_entrypoint("demo", adapter=adapter)

    computed = run_tables(publication)[0]

    assert computed.bodies == (((1, 2),),)
    assert computed.metadata == {"formats": ("{:.1f}", "{}")}


def test_command_registry_dispatches_core_commands_and_writes_results(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "sample.txt").write_text("value", encoding="utf-8")
    entrypoint = tmp_path / "figures.py"
    entrypoint.write_text(
        "\n".join([
            "from pubify_data import data, figure",
            "@data('sample.txt')",
            "def load_sample(ctx, path):",
            "    return path.read_text(encoding='utf-8')",
            "@figure",
            "def plot_demo(ctx, sample):",
            "    return sample",
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = PublicationAdapter("demo", entrypoint=entrypoint, data_root=data_root)
    publication = load_publication_from_entrypoint("demo", adapter=adapter)
    registry = CommandRegistry()
    register_core_commands(registry)

    assert registry.dispatch(CoreCommandContext(publication), ("figure", "list")) == 0
    assert capsys.readouterr().out == "demo\n"

    class Writer:
        def __init__(self) -> None:
            self.figures: object | None = None

        def write_figures(self, results: object) -> None:
            self.figures = results

    writer = Writer()

    assert registry.dispatch(CoreCommandContext(publication, artifact_writer=writer), ("figure", "update")) == 0
    assert writer.figures is not None

    with pytest.raises(TypeError, match="Artifact writer must implement write_figures"):
        registry.dispatch(CoreCommandContext(publication, artifact_writer=object()), ("figure", "update"))


def test_npz_helpers_use_downstream_resolver(tmp_path: Path) -> None:
    def resolver(workspace_root: Path, publication_id: str) -> Path:
        return workspace_root / "output" / publication_id

    saved = save_publication_data_npz("demo", "sample.npz", workspace_root=tmp_path, data_root_resolver=resolver, values=np.array([1.0]))

    assert saved == tmp_path / "output" / "demo" / "sample.npz"
    assert np.array_equal(load_publication_data_npz(saved)["values"], np.array([1.0]))

    with pytest.raises(ValueError, match="must be a non-empty relative path"):
        save_publication_data_npz("demo", "", workspace_root=tmp_path, data_root_resolver=resolver, values=np.array([1.0]))
