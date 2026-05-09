# Dashboard Section Writer Matrix

This matrix lists dashboard-facing README-style example sections whose writer dry-runs are covered in clean Docker verification. It complements the checked dashboard fixture registry by proving readiness and schema writer modes can target each registered dashboard snippet without mutating docs.

| Markdown path | Section | Example type | Docker-covered writer command |
| --- | --- | --- | --- |
| `docs/usage-examples.md` | First JSON and Markdown fences | Standalone readiness report examples | `r-project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/usage-examples.md` |
| `docs/dashboard-schema.md` | Memory overlap demo JSON Schemas | Standalone compact memory-overlap schema example | `r-project --root . --write-readme-schema-examples --dry-run-readme-schema-examples --readme-schema-path docs/dashboard-schema.md` |
| `docs/dashboard-index.md` | First JSON and Markdown fences | Combined dashboard readiness report examples | `r-project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/dashboard-index.md` |
| `docs/dashboard-index.md` | First schema JSON fence | Combined dashboard memory-overlap schema example | `r-project --root . --write-readme-schema-examples --dry-run-readme-schema-examples --readme-schema-path docs/dashboard-index.md` |
| `docs/usage-examples.md` | Variant `compact` first JSON and Markdown fences | Variant `compact` standalone readiness report examples | `r-project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/usage-examples.md` |
| `docs/dashboard-schema.md` | Variant `compact` memory overlap demo JSON Schemas | Variant `compact` standalone compact memory-overlap schema example | `r-project --root . --write-readme-schema-examples --dry-run-readme-schema-examples --readme-schema-path docs/dashboard-schema.md` |
| `docs/dashboard-index.md` | Variant `compact` first JSON and Markdown fences | Variant `compact` combined dashboard readiness report examples | `r-project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/dashboard-index.md` |
| `docs/dashboard-index.md` | Variant `compact` first schema JSON fence | Variant `compact` combined dashboard memory-overlap schema example | `r-project --root . --write-readme-schema-examples --dry-run-readme-schema-examples --readme-schema-path docs/dashboard-index.md` |

Run the matrix guard after adding dashboard readiness/schema sections or writer dry-runs:

```bash
r-project --root . --check-dashboard-section-writer-matrix
r-project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
```
