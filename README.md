# pubify-data

`pubify-data` is the TeX-agnostic upstream runtime for reusable publication data loaders and computed artifacts.

It provides decorators, entrypoint discovery, dependency-aware runtime execution, neutral figure/stat/table result models, pinned data helpers, and a small explicit CLI command framework. It does not provide a console script and does not own downstream workspace roots, renderer output formats, LaTeX, or build behavior.

Downstream packages, such as `pubify-pubs`, use `pubify-data` to implement their own CLI and rendering workflows.
