# AGENTS.md

## Scope
- Documentation surface profile: public-python.

## Source Of Truth Docs
- Follow `README.md` for the public overview and starting docs.
- Follow `docs/architecture.md` for package boundaries, public APIs, persisted contracts, and runtime lifecycle behavior.
- Follow `docs/testing.md` for canonical verification commands and completion expectations.
- Follow `docs/development.md` for local setup, environment, packaging, and docs-build behavior.
- Follow `CONTRIBUTING.md` for contributor and release workflow.

## Shared Validation

- Use `$agent-surface-review` for shared agent-surface review.
- Use `$documentation-surface-review` for documentation-surface review with the `public-python` profile.
- Use `$code-quality-review` for source-code quality review.

## Skill Requirements
- For Python code, use `$python-code-writing`.
- For project docs such as `docs/architecture.md`, `docs/testing.md`, `docs/development.md`, and similar long-lived project documents, use `$project-docs-writing`.
- For `README.md`, use `$readme-writing`.
- For plan documents or phased execution docs when they are created or revised, use `$plan-writing`.

## Astro-Agents Integration
- `astro-agents` owns the shared `$pubify-authoring` skill used by agents working on downstream pubify publication and presentation workflows.
- When this project changes user-facing `pubify-data` behavior, update the corresponding shared `astro-agents` skill references under `skills/pubify-authoring/references/`.
- Examples that require an `astro-agents` update include decorator behavior, loader signatures, `ctx` behavior, dependency execution, source reuse, figure/stat/table result models, and data ownership or path rules.

## Working Rules
- Keep repo-specific commands, package boundaries, contracts, lifecycle rules, and exceptions in the repo docs rather than in this file.
- Use `docs/architecture.md` as the source of truth for what belongs in `pubify-data` versus downstream packages.
- Before finishing shared runtime or adapter changes, run the verification expected by `docs/testing.md`.
- Keep downstream layout, rendering, and build concerns out of this package.
