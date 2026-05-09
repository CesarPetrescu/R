from pathlib import Path


def test_docker_test_harness_exists_and_runs_full_verification():
    compose_file = Path("docker-compose.yml")
    dockerfile = Path("Dockerfile")

    assert dockerfile.exists()
    assert compose_file.exists()

    dockerfile_text = dockerfile.read_text(encoding="utf-8")
    compose_text = compose_file.read_text(encoding="utf-8")

    assert "python:3.11-slim" in dockerfile_text
    assert "pip install -e ." in dockerfile_text
    assert "python -m pytest -q" in compose_text
    assert "python -m r_project.lint --root ." in compose_text
    assert "python -m r_project --root . --json" in compose_text
    assert "python -m r_project --root . --markdown" in compose_text
    assert "python -m r_project --root . --json --fail-on-blockers" in compose_text
    assert "python -m r_project --root . --check-readme-examples" in compose_text
    assert "python -m r_project --root . --generate-readme-examples" in compose_text
    assert "python -m r_project --root . --write-readme-examples" in compose_text
    assert "python -m r_project --root . --write-readme-examples --dry-run-readme-examples" in compose_text
    assert "python -m r_project --root . --check-readme-examples --readme-examples-path README.md" in compose_text
    assert (
        "python -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path README.md"
        in compose_text
    )
    assert "python -m r_project --root . --check-readme-examples --readme-examples-path docs/usage-examples.md" in compose_text
    assert (
        "python -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/usage-examples.md"
        in compose_text
    )
    assert "python -m r_project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md" in compose_text
    assert (
        "python -m r_project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/automation-index.md --readme-examples-section 'Embedded readiness report example'"
        in compose_text
    )
    assert "python -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md" in compose_text
    assert (
        "python -m r_project --root . --write-readme-schema-examples --dry-run-readme-schema-examples --readme-schema-path docs/automation-index.md --readme-schema-section 'Embedded memory-overlap schema example'"
        in compose_text
    )
    assert "python -m r_project --root . --check-readme-examples --readme-examples-path docs/automation-index.md" in compose_text
    assert "python -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/automation-index.md" in compose_text
    assert "python -m r_project --memory-threshold-demo" in compose_text
    assert "python -m r_project --memory-threshold-demo --json" in compose_text
    assert "python -m r_project --memory-threshold-demo --memory-overlap-max-count 2 --memory-overlap-max-bytes 6" in compose_text
    assert "python -m r_project --memory-threshold-demo --json --memory-overlap-max-count 2 --memory-overlap-max-bytes 6" in compose_text
    assert "python -m r_project --memory-threshold-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2" in compose_text
    assert "python -m r_project --memory-threshold-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2" in compose_text
    assert "python -m r_project --memory-overlap-totals-demo" in compose_text
    assert "python -m r_project --memory-overlap-totals-demo --json" in compose_text
    assert "python -m r_project --memory-overlap-totals-demo --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2" in compose_text
    assert "python -m r_project --memory-overlap-totals-demo --json --memory-overlap-group-by name_prefix --memory-overlap-prefix-depth 2" in compose_text
    assert "python -m r_project --memory-overlap-totals-demo --memory-overlap-name-prefix left." in compose_text
    assert "python -m r_project --memory-threshold-demo --json --memory-overlap-tag source:literal --memory-overlap-max-count 0" in compose_text
    assert "python -m r_project --memory-overlap-demo-schema" in compose_text
    assert "python -m r_project --root . --check-memory-overlap-demo-schema" in compose_text
    assert "python -m r_project --root . --check-readme-schema-examples" in compose_text
    assert "python -m r_project --root . --write-readme-schema-examples --dry-run-readme-schema-examples" in compose_text
    assert (
        "python -m r_project --root . --check-readme-schema-examples --readme-schema-path README.md" in compose_text
    )
    assert (
        "python -m r_project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-schema.md"
        in compose_text
    )
    assert "python -m r_project --root . --check-changelog-version" in compose_text
    assert "python -m r_project --root . --check-release-tag v0.1.0 --docker-verified --skip-git-clean-check" in compose_text
    assert "python -m r_project --root . --json --check-release-tag v0.1.0 --docker-verified --skip-git-clean-check" in compose_text
    assert "python -m r_project --root . --check-release-tag-fixture" in compose_text
    assert "python -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture" in compose_text
    assert (
        "python -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-path tests/fixtures/release-tag-checklist.json"
        in compose_text
    )
    assert (
        "python -m r_project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-version 0.2.0"
        in compose_text
    )
    assert "python -m r_project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json" in compose_text
    assert (
        "python -m r_project --root . --check-release-examples --release-examples-path docs/release-examples.md"
        in compose_text
    )
    assert (
        "python -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/release-examples.md"
        in compose_text
    )
    assert (
        "python -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md"
        in compose_text
    )
    assert (
        "python -m r_project --root . --check-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'"
        in compose_text
    )
    assert (
        "python -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'"
        in compose_text
    )
    assert (
        "python -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'"
        in compose_text
    )
    assert (
        "python -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-path tests/fixtures/automation-index-release-smoke.md --release-examples-section 'Embedded release checklist example'"
        in compose_text
    )
    assert (
        "python -m r_project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md"
        in compose_text
    )
    assert "python -m r_project --root . --check-release-example-fixtures" in compose_text
    assert "python -m r_project --root . --check-release-example-sections" in compose_text
    assert "python -m r_project --root . --check-release-section-writer-matrix" in compose_text
    assert (
        "python -m r_project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0"
        in compose_text
    )
    assert (
        "python -m r_project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0"
        in compose_text
    )
    assert "python -m r_project --root . --check-release-examples-path-safety" in compose_text
    assert "python -m r_project --root . --check-automation-index-links" in compose_text
    assert "python -m r_project --root . --check-automation-index-commands" in compose_text
    assert "python -m r_project --root . --check-automation-command-fixtures" in compose_text
    assert "python -m r_project --root . --check-dashboard-example-fixtures" in compose_text
    assert "python -m r_project --root . --check-dashboard-section-writer-matrix" in compose_text
    assert (
        "python -m r_project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact"
        in compose_text
    )
    assert (
        "python -m r_project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact"
        in compose_text
    )
    assert (
        "python -m r_project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact"
        in compose_text
    )
