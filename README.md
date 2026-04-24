# pubify-data

`pubify-data` is the TeX-agnostic upstream runtime for reusable publication data loaders and computed artifacts.

It provides decorators, entrypoint discovery, dependency-aware runtime execution, neutral figure/stat/table result models, pinned data helpers, neutral artifact namespace helpers, and a small explicit CLI command framework. It does not provide a console script and does not own downstream workspace roots, renderer output formats, LaTeX, or build behavior.

Downstream packages, such as `pubify-pubs`, use `pubify-data` to implement their own CLI and rendering workflows.

## Downstream Integration

A downstream package resolves its own workspace schema first, then passes a
`PublicationAdapter` into `pubify-data`:

```python
import pubify_data

adapter = pubify_data.PublicationAdapter(
    publication_id="my-paper",
    publication_root=publication_root,
    entrypoint=publication_root / "figures.py",
    data_root=data_root,
    external_data_roots=external_data_roots,
    workspace=pubify_data.WorkspaceAdapter(workspace_root),
)
publication = pubify_data.load_publication_from_entrypoint("my-paper", adapter=adapter)
```

The adapter is the boundary: downstream packages own root names, config layout,
renderers, generated artifact paths, and build commands.

Downstreams that need framework-owned generated artifacts can reserve neutral
namespaces under their resolved data root:

```python
artifacts_root = pubify_data.artifact_namespace_root(data_root, "tex-artifacts", create=True)
stats_path = pubify_data.artifact_namespace_path(
    data_root,
    "tex-artifacts",
    "autostats.tex",
    create_parent=True,
)
```

The namespace names and artifact filenames still belong to the downstream
package; `pubify-data` only validates that they stay under the supplied data
root.

Downstream CLIs can compose the reusable neutral command registry and attach
their own artifact writer:

```python
registry = pubify_data.CommandRegistry()
pubify_data.register_core_commands(registry)
context = pubify_data.CoreCommandContext(
    publication=publication,
    artifact_writer=writer,
)
result = registry.dispatch(context, tuple(argv))
```

The core registry covers neutral `data`, `figure`, `stat`, `table`, and
`update` list/update flows. Downstream CLIs keep executable names, rendering,
preview, build, shell, and format-specific commands in their own package.
