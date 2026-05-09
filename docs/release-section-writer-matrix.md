# Release Section Writer Matrix

This matrix lists the release checklist Markdown sections whose writer dry-runs are covered in clean Docker verification. It complements the checked section registry by proving both current-version and configurable future-version writer modes can target each registered release snippet without mutating docs.

| Markdown path | Section | Version target | Docker-covered writer command |
| --- | --- | --- | --- |
| `docs/release-examples.md` | First JSON fence | Current package version | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/release-examples.md` |
| `docs/release-examples.md` | First JSON fence | Future package version `0.2.0` | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md` |
| `docs/automation-index.md` | Embedded release checklist example | Current package version | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'` |
| `docs/automation-index.md` | Embedded release checklist example | Future package version `0.2.0` | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'` |

Run the matrix guard after adding release checklist sections or future-version snippets:

```bash
r-project --root . --check-release-section-writer-matrix
r-project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
```
