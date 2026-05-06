import subprocess
import sys
from pathlib import Path
import tomllib


def test_pyproject_exposes_lint_console_script():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["r-project-lint"] == "r_project.lint:main"


def test_lint_command_accepts_valid_python_sources(tmp_path):
    source_dir = tmp_path / "src"
    tests_dir = tmp_path / "tests"
    source_dir.mkdir()
    tests_dir.mkdir()
    (source_dir / "ok.py").write_text("value = 1\n", encoding="utf-8")
    (tests_dir / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "r_project.lint", "--root", str(tmp_path)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PYTHONPATH": str(Path.cwd() / "src")},
    )

    assert result.returncode == 0
    assert "Syntax check passed" in result.stdout
    assert result.stderr == ""


def test_lint_command_rejects_invalid_python_sources(tmp_path):
    source_dir = tmp_path / "src"
    tests_dir = tmp_path / "tests"
    source_dir.mkdir()
    tests_dir.mkdir()
    (source_dir / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "r_project.lint", "--root", str(tmp_path)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PYTHONPATH": str(Path.cwd() / "src")},
    )

    assert result.returncode == 1
    assert "Syntax check failed" in result.stdout
    assert "broken.py" in result.stdout


def test_readme_documents_lint_command():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "r-project-lint --root ." in readme
    assert "PYTHONPATH=src python3 -m r_project.lint --root ." in readme


def test_docker_verification_runs_lint_command():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "python -m r_project.lint --root ." in compose
