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
- result models: `FigureResult`, `FigurePanel`, `StatResult`, `TableResult`
- CLI helpers: `CommandRegistry`, `CoreCommandContext`, `register_core_commands`

## Downstream Adapters

Downstream packages own roots and artifact output. They pass a resolved `PublicationAdapter` and optional `ArtifactWriter` callbacks into `pubify-data` rather than relying on package-wide root assumptions.
