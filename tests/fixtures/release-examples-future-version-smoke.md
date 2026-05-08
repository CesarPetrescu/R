# Release Checklist Future-Version Smoke Fixture

This compact fixture intentionally starts with the current package version so a future-version dry-run can prove preview output changes without mutating checked current-version docs.

```json
{"checks": {"docker_verified": true, "git_clean": "skipped", "tag_matches_version": true}, "expected_tag": "v0.1.0", "ready": true, "tag": "v0.1.0", "version": "0.1.0"}
```
