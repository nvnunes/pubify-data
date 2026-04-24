# pubify-data

`pubify-data` is the TeX-agnostic upstream runtime for reusable publication data loaders and computed artifacts.

It is intended for downstream packages that provide their own workspace roots, CLI executable, renderers, and build behavior.

Use `PublicationAdapter` and `WorkspaceAdapter` to pass resolved downstream
paths into the runtime. Use `CommandRegistry` and `register_core_commands(...)`
when a downstream CLI wants to reuse neutral list/update behavior while keeping
format-specific commands local.
