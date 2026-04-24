# Architecture

This document is the source of truth for `pubify-data` package boundaries and reusable runtime contracts.

## Role

`pubify-data` owns the TeX-agnostic runtime shared by downstream publication workflow packages.

It intentionally does not own downstream workspace root schemas. A downstream package supplies an adapter that resolves publication roots, data roots, entrypoints, and artifact persistence.

## Public Surface

Primary public entrypoints are:

- decorators: `data`, `external_data`, `figure`, `stat`, `table`
- config helpers: `find_workspace_root`, `load_pubify_config`, `load_config_section`
- adapter contracts: `WorkspaceAdapter`, `PublicationAdapter`, `ArtifactWriter`
- discovery helpers: `load_publication_from_entrypoint`, `discover_publication`
- runtime helpers: `build_run_context`, `resolve_loader`, `validate_dependencies`, `run_figures`, `run_stats`, `run_tables`
- data helpers: `publication_data_path`, `save_publication_data_npz`, `load_publication_data_npz`
- artifact namespace helpers: `artifact_namespace_root`, `artifact_namespace_path`
- result models: `FigureResult`, `FigurePanel`, `StatResult`, `TableResult`
- CLI helpers: `CommandRegistry`, `CoreCommandContext`, `register_core_commands`

## Downstream Adapters

Downstream packages own roots and artifact output. They pass a resolved `PublicationAdapter` and optional `ArtifactWriter` callbacks into `pubify-data` rather than relying on package-wide root assumptions.

The expected adapter flow is:

1. A downstream package finds its workspace and parses its own config section.
2. It resolves publication roots, the entrypoint path, the pinned data root, and
   any named external data roots.
3. It builds a `WorkspaceAdapter` and `PublicationAdapter`.
4. It calls `load_publication_from_entrypoint(...)`.
5. It runs neutral runtime helpers and converts neutral results into
   downstream-specific files, renderers, or build artifacts.

For example:

```python
adapter = PublicationAdapter(
    publication_id=publication_id,
    publication_root=publication_root,
    entrypoint=publication_root / "figures.py",
    data_root=data_root,
    external_data_roots=external_data_roots,
    workspace=WorkspaceAdapter(workspace_root, config=workspace_config),
)
publication = load_publication_from_entrypoint(publication_id, adapter=adapter)
```

`pubify-data` must not infer downstream root names such as
`publications_root`, `data_root`, `tex`, `autofigures`, or build directories.
Those names belong to downstream packages.

Downstreams may use `artifact_namespace_root(...)` and
`artifact_namespace_path(...)` to reserve generated-artifact namespaces under a
resolved publication `data_root`. These helpers only validate and join paths;
they do not define artifact names, formats, lifecycle, or manuscript-facing
views.

## Reusable CLI Composition

`CommandRegistry` is a small dispatch layer for downstream CLIs. It lets a
downstream package reuse neutral list/update flows while keeping executable
names and format-specific commands outside `pubify-data`.

```python
registry = CommandRegistry()
register_core_commands(registry)

context = CoreCommandContext(
    publication=publication,
    artifact_writer=artifact_writer,
    loader_cache=loader_cache,
)
status = registry.dispatch(context, tuple(argv))
```

The reusable commands are:

- `data list`
- `figure list`
- `figure update`
- `stat list`
- `stat update`
- `table list`
- `table update`
- `update`

Downstream packages remain responsible for user-facing command names, argument
parsing, output formatting, preview/build/shell behavior, and persistence. If a
downstream wants neutral update commands to write files, it supplies an
`ArtifactWriter` that converts neutral figure/stat/table results into its own
artifact format.
