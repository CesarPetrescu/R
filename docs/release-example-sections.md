# Release Example Section Registry

This registry lists every Markdown release checklist example section that is checked independently. It is intentionally small and command-focused so future release docs can embed multiple named checklist snippets without losing Docker coverage.

| Markdown path | Section | Docker verification command |
| --- | --- | --- |
| `docs/release-examples.md` | First JSON fence | `r-project --root . --check-release-examples --release-examples-path docs/release-examples.md` |
| `docs/automation-index.md` | Embedded release checklist example | `r-project --root . --check-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'` |

Run the registry guard after adding or renaming a release checklist example section:

```bash
r-project --root . --check-release-example-sections
```
