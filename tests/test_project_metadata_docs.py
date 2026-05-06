from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_release_versioning_policy():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Release and versioning" in readme
    assert "0.1.0" in readme
    assert "CHANGELOG.md" in readme
    assert "semantic versioning" in readme.lower()


def test_changelog_tracks_unreleased_changes():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "# Changelog" in changelog
    assert "## Unreleased" in changelog
    assert "release/versioning policy" in changelog


def test_license_file_declares_project_license():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert "MIT License" in license_text
    assert "Project R contributors" in license_text
