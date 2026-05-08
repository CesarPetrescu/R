# Dashboard Schema Examples

Standalone dashboard-facing compact JSON Schema examples for the memory-overlap demo payloads.

Dashboard consumers can validate the full schema surface with:

```bash
r-project --memory-overlap-demo-schema
```

Use the on-demand drift guard to keep this standalone document synchronized with current CLI output:

```bash
r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-schema.md
```

Preview or refresh the checked JSON fence with:

```bash
r-project --root . --write-readme-schema-examples --dry-run-readme-schema-examples --readme-schema-path docs/dashboard-schema.md
r-project --root . --write-readme-schema-examples --readme-schema-path docs/dashboard-schema.md
```

## Memory overlap demo JSON Schemas

```json
{"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"memoryOverlapTotalsDemo": {"required": ["by", "totals"], "totals_item": {"required": ["group", "overlap_count", "total_overlap_size"]}}, "memoryThresholdDemo": {"required": ["by", "max_overlap_count", "max_total_overlap_size", "violations"], "violations_item": {"required": ["group", "overlap_count", "total_overlap_size", "max_overlap_count", "max_total_overlap_size", "exceeded"]}}}}
```
