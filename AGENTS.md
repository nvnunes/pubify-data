# pubify-data Development Notes

Use the shared `astro-agents` guidance for public Python project structure, Python development, and agent-surface conventions.

`pubify-data` is the TeX-agnostic upstream runtime for publication data loaders and computed artifacts. Keep downstream layout, rendering, and build concerns out of this package.

## Package Boundaries

Package-owned:

- generic `pubify.yaml` discovery and namespaced config loading
- decorators for data loaders, figures, stats, and tables
- publication entrypoint import and decorated-object discovery
- loader dependency validation and cached runtime execution
- neutral figure, stat, and table result models
- reusable CLI command registry and core list/update command helpers
- pinned data path helpers through downstream-provided data-root resolvers
- neutral artifact namespace helpers under downstream-provided data roots

Downstream-owned:

- workspace root schemas and root names
- publication-local config schemas beyond generic external data roots
- generated artifact filenames and persistence
- renderer-specific escaping, snippets, previews, and builds
- project-specific CLI executable names and extra commands

## Verification

Canonical package test command:

- `pytest tests -q`
