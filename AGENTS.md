# pubify-data Development Notes

Use the shared `astro-agents` guidance for public Python project structure, Python development, and agent-surface conventions.

`pubify-data` is the TeX-agnostic upstream runtime for publication data loaders and computed artifacts. Keep downstream layout, rendering, and build concerns out of this package.

## Scope

- Documentation surface profile: public-python.

## First Reads

- Read `docs/architecture.md` before changing package boundaries, public APIs, persisted contracts, or runtime lifecycle behavior.
- Read `docs/testing.md` before concluding substantial work or changing shared runtime behavior.
- Read `docs/development.md` before changing bootstrap, environment, packaging, or docs-build behavior.

## Working Rules

- Keep repo-specific commands, package boundaries, contracts, lifecycle rules, and exceptions in the repo docs rather than in this file.
- Use `docs/architecture.md` as the source of truth for what belongs in `pubify-data` versus downstream packages.
- Before finishing shared runtime or adapter changes, run the verification expected by `docs/testing.md`.
