from pathlib import Path
import tomllib


def test_pyproject_exposes_r_project_console_script():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"] == {
        "r-project": "r_project.__main__:main",
        "r-project-lint": "r_project.lint:main",
    }


def test_readme_documents_editable_install_and_console_script_usage():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "python3 -m pip install -e ." in readme
    assert "r-project --root . --json" in readme
    assert "r-project --root . --markdown" in readme
