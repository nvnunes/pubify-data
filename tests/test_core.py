from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from pubify_data import (
    CommandRegistry,
    CoreCommandContext,
    PublicationAdapter,
    UserCodeExecutionError,
    build_run_context,
    data,
    figure,
    load_publication_from_entrypoint,
    register_core_commands,
    run_figures,
    run_stats,
    stat,
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


def test_npz_helpers_use_downstream_resolver(tmp_path: Path) -> None:
    def resolver(workspace_root: Path, publication_id: str) -> Path:
        return workspace_root / "output" / publication_id

    saved = save_publication_data_npz("demo", "sample.npz", workspace_root=tmp_path, data_root_resolver=resolver, values=np.array([1.0]))

    assert saved == tmp_path / "output" / "demo" / "sample.npz"
    assert np.array_equal(load_publication_data_npz(saved)["values"], np.array([1.0]))
