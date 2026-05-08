# Dashboard Example Fixture Registry

This registry maps dashboard-facing README-style example surfaces to the exact `r-project` commands that Docker verification must exercise. Use it when dashboard docs split readiness or schema examples across multiple independently checked Markdown sections.

| Markdown path | Purpose | Docker verification command |
| --- | --- | --- |
| `docs/usage-examples.md` | Standalone readiness report JSON and Markdown examples. | `r-project --root . --check-readme-examples --readme-examples-path docs/usage-examples.md` |
| `docs/dashboard-schema.md` | Standalone compact memory-overlap JSON Schema example. | `r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-schema.md` |
| `docs/dashboard-index.md` | Combined dashboard readiness report examples. | `r-project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md` |
| `docs/dashboard-index.md` | Combined dashboard memory-overlap schema example. | `r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md` |

Before publishing dashboard docs, run:

```bash
r-project --root . --check-dashboard-example-fixtures
```
