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
    assert "r-project --root . --check-changelog-version" in text
    assert "r-project --root . --check-release-tag v0.1.0 --docker-verified" in text
    assert "r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json" in text
    assert "docker compose run --build --rm test" in text


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
