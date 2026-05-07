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
