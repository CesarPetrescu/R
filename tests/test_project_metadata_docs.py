import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_release_versioning_policy():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Release and versioning" in readme
    assert "0.1.0" in readme
    assert "--check-release-tag v0.1.0 --docker-verified" in readme
    assert "--json --check-release-tag v0.1.0 --docker-verified" in readme
    assert "semantic versioning" in readme.lower()


def test_release_checklist_document_explains_external_fixture_path():
    release_doc = ROOT / "docs" / "release-checklist.md"

    assert release_doc.exists()
    text = release_doc.read_text(encoding="utf-8")
    assert "# Release Checklist Fixtures" in text
    assert "r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json" in text
    assert "r-project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json" in text
    assert "docker compose run --build --rm test" in text


def test_release_readiness_index_links_release_docs_and_guard_commands():
    index_doc = ROOT / "docs" / "release-index.md"

    assert index_doc.exists()
    text = index_doc.read_text(encoding="utf-8")
    assert "# Release Readiness Index" in text
    assert "[release checklist fixture workflow](release-checklist.md)" in text
    assert "[checked release checklist JSON](release/checklist.json)" in text
    assert "[checked release checklist examples](release-examples.md)" in text
    assert "r-project --root . --check-changelog-version" in text
    assert "r-project --root . --check-release-tag v0.1.0 --docker-verified" in text
    assert "r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json" in text
    assert "r-project --root . --check-release-examples --release-examples-path docs/release-examples.md" in text
    assert "--release-examples-version 0.2.0" in text
    assert "docker compose run --build --rm test" in text


def test_release_examples_document_fixture_matches_current_cli_output():
    examples_doc = ROOT / "docs" / "release-examples.md"

    assert examples_doc.exists()
    text = examples_doc.read_text(encoding="utf-8")
    assert "# Release Checklist Examples" in text
    assert "r-project --root . --check-release-examples --release-examples-path docs/release-examples.md" in text
    assert "--release-examples-version 0.2.0" in text
    assert '"tag": "v0.1.0"' in text
    env = os.environ | {"PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(ROOT),
            "--check-release-examples",
            "--release-examples-path",
            "docs/release-examples.md",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "docs/release-examples.md release checklist example matches current CLI output.\n"
    assert result.stderr == ""


def test_autonomous_automation_index_links_dashboard_and_release_surfaces():
    index_doc = ROOT / "docs" / "automation-index.md"

    assert index_doc.exists()
    text = index_doc.read_text(encoding="utf-8")
    assert "# Automation Index" in text
    assert "[dashboard readiness/schema index](dashboard-index.md)" in text
    assert "[release readiness index](release-index.md)" in text
    assert "[release example fixture index](release-example-fixtures.md)" in text
    assert "r-project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md" in text
    assert "r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md" in text
    assert "r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json" in text
    assert "--release-examples-version 0.2.0" in text
    assert "docker compose run --build --rm test" in text


def test_release_example_fixture_index_links_each_fixture_and_docker_command():
    index_doc = ROOT / "docs" / "release-example-fixtures.md"
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert index_doc.exists()
    text = index_doc.read_text(encoding="utf-8")
    assert "# Release Example Fixture Index" in text
    assert "tests/fixtures/automation-index-release-smoke.md" in text
    assert "tests/fixtures/release-examples-future-version-smoke.md" in text
    assert (
        "r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path tests/fixtures/automation-index-release-smoke.md --release-examples-section 'Embedded release checklist example'"
        in text
    )
    assert (
        "r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md"
        in text
    )
    assert "docker compose run --build --rm test" in text
    for fixture in (
        "tests/fixtures/automation-index-release-smoke.md",
        "tests/fixtures/release-examples-future-version-smoke.md",
    ):
        assert fixture in text
        assert fixture in compose_text


def test_readme_links_combined_automation_index():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "[`docs/automation-index.md`](docs/automation-index.md)" in readme


def test_release_checklist_document_fixture_matches_current_cli_output():
    fixture = ROOT / "docs" / "release" / "checklist.json"

    assert fixture.exists()
    text = fixture.read_text(encoding="utf-8")
    assert '\"tag\": \"v0.1.0\"' in text
    assert '\"ready\": true' in text
    env = os.environ | {"PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r_project",
            "--root",
            str(ROOT),
            "--check-release-tag-fixture",
            "--release-tag-fixture-path",
            "docs/release/checklist.json",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == "docs/release/checklist.json release tag checklist fixture matches current CLI output.\n"
    assert result.stderr == ""


def test_changelog_tracks_unreleased_changes():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "# Changelog" in changelog
    assert "## Unreleased" in changelog
    assert "release/versioning policy" in changelog


def test_license_file_declares_project_license():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert license_text.startswith("GNU AFFERO GENERAL PUBLIC LICENSE")
    assert "Version 3, 19 November 2007" in license_text
    assert "Appropriate Legal Notices" in license_text
