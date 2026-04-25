# Testing

This document is the source of truth for `pubify-data` verification.

## Package Tests

Canonical command from the repo root:

```sh
python -m pytest tests -q
```

When using the repo-local Conda environment:

```sh
./.conda/bin/python -m pytest tests -q
```

## Documentation Build

Run the strict docs build after changing public docs, docstrings used by the API
reference, MkDocs configuration, or public package metadata:

```sh
python -m mkdocs build --strict
```

With the repo-local Conda environment:

```sh
./.conda/bin/mkdocs build --strict
```

## Downstream Smoke Tests

Run downstream tests after changing adapter contracts, public runtime behavior,
result models, source publication behavior, artifact writer behavior, or
decorator/discovery behavior.

Expected downstream smoke checks when sibling checkouts are available:

```sh
cd ../pubify-pubs
./.conda/bin/python -m pytest tests -q

cd ../pubify-ppt
./.conda/bin/python -m pytest tests -q
```

If a downstream repo is already in a dirty or failing state, record the failure
and distinguish it from the `pubify-data` change under review.
