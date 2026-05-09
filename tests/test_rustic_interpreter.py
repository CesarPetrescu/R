import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def compile_rustic_driver(tmp_path: Path) -> Path:
    binary = tmp_path / "rustic-expression-demo"
    result = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(ROOT / "runtime" / "include"),
            str(ROOT / "runtime" / "rustic.c"),
            str(ROOT / "tests" / "fixtures" / "rustic_expression_driver.c"),
            "-o",
            str(binary),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 0, result.stderr
    return binary


def test_c_hosted_rustic_interpreter_evaluates_integer_expression(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "1 + 2 * 3"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "1 + 2 * 3 => 7\n"


def test_c_hosted_rustic_interpreter_reports_invalid_expression(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "1 + * 3"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "expected integer" in result.stderr


def test_c_hosted_rustic_interpreter_evaluates_let_binding_statement(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "let x = 2 + 3; x * 4"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "let x = 2 + 3; x * 4 => 20\n"


def test_c_hosted_rustic_interpreter_reports_undefined_identifiers(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "missing + 1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "undefined identifier" in result.stderr


def test_c_hosted_rustic_interpreter_sequences_expression_statements(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "1 + 2; 3 * 4; 5 + 6"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "1 + 2; 3 * 4; 5 + 6 => 11\n"


def test_c_hosted_rustic_interpreter_rejects_empty_program(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "   "],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "expected integer" in result.stderr
