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


def test_c_hosted_rustic_interpreter_updates_existing_binding(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "let x = 1; x = x + 2; x"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "let x = 1; x = x + 2; x => 3\n"


def test_c_hosted_rustic_interpreter_rejects_assignment_to_undefined_name(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "x = 3"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "undefined identifier" in result.stderr


def test_c_hosted_rustic_interpreter_honors_parenthesized_expression_precedence(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "(1 + 2) * 3"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "(1 + 2) * 3 => 9\n"


def test_c_hosted_rustic_interpreter_rejects_unmatched_parentheses(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "(1 + 2"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "expected closing parenthesis" in result.stderr


def test_c_hosted_rustic_interpreter_evaluates_equal_comparison_to_boolean_integer(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "let x = 3; x == 3"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "let x = 3; x == 3 => 1\n"


def test_c_hosted_rustic_interpreter_evaluates_non_equal_comparison_to_zero(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "let x = 3; x == 4"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "let x = 3; x == 4 => 0\n"


def test_c_hosted_rustic_interpreter_evaluates_not_equal_comparison(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "let x = 3; x != 4"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "let x = 3; x != 4 => 1\n"


def test_c_hosted_rustic_interpreter_evaluates_ordering_comparisons(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    expectations = {
        "1 + 2 < 2 * 2": 1,
        "4 <= 4": 1,
        "5 > 9": 0,
        "5 >= 5": 1,
    }
    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_evaluates_subtraction_with_additive_precedence(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "10 - 3 + 2 * 4"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 15\n"


def test_c_hosted_rustic_interpreter_rejects_single_bang_inside_expression(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "1 ! 1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "expected operator" in result.stderr


def test_c_hosted_rustic_interpreter_rejects_single_equals_inside_expression(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "1 = 1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "expected operator" in result.stderr


def test_c_hosted_rustic_interpreter_rejects_missing_right_comparison_operand(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "1 == "],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "expected integer" in result.stderr


def test_c_hosted_rustic_interpreter_evaluates_block_expression(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "{ let x = 2; x + 1 }"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "{ let x = 2; x + 1 } => 3\n"


def test_c_hosted_rustic_interpreter_keeps_block_bindings_scoped(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "{ let x = 2; x }; x"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "undefined identifier" in result.stderr


def test_c_hosted_rustic_interpreter_rejects_unclosed_block_expression(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "{ let x = 2; x + 1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "expected closing brace" in result.stderr


def test_c_hosted_rustic_interpreter_evaluates_if_else_true_branch(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "if 1 < 2 { let x = 3; x + 4 } else { missing }"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "if 1 < 2 { let x = 3; x + 4 } else { missing } => 7\n"


def test_c_hosted_rustic_interpreter_evaluates_if_else_false_branch(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "let x = 5; if x == 4 { missing } else { x * 2 }"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "let x = 5; if x == 4 { missing } else { x * 2 } => 10\n"


def test_c_hosted_rustic_interpreter_keeps_if_branch_bindings_scoped(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "if 1 { let x = 2; x } else { 0 }; x"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "undefined identifier" in result.stderr


def test_c_hosted_rustic_interpreter_evaluates_while_loop_mutation(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "let i = 0; let total = 0; while i < 4 { total = total + i; i = i + 1; }; total"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 6\n"


def test_c_hosted_rustic_interpreter_skips_false_while_body(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "let x = 3; while 0 { missing }; x"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 3\n"


def test_c_hosted_rustic_interpreter_evaluates_named_function_call(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn add(a, b) { a + b }; add(2, 3)"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 5\n"


def test_c_hosted_rustic_interpreter_evaluates_nested_function_composition(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn add(a, b) { a + b }; fn twice(x) { add(x, x) }; twice(add(2, 3))"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 10\n"


def test_c_hosted_rustic_interpreter_evaluates_recursive_countdown_function(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn countdown(n) { if n == 0 { 7 } else { countdown(n - 1) } }; countdown(3)"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 7\n"


def test_c_hosted_rustic_interpreter_rejects_runaway_recursive_function_with_step_limit(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn forever(n) { forever(n) }; forever(1)"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "step limit exceeded" in result.stderr


def test_c_hosted_rustic_interpreter_keeps_function_parameters_scoped(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn id(value) { value }; id(4); value"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "undefined identifier" in result.stderr


def test_c_hosted_rustic_interpreter_rejects_unknown_function_calls(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "missing(1)"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "undefined identifier" in result.stderr


def test_c_hosted_rustic_interpreter_rejects_function_argument_count_mismatch(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn one(x) { x }; one(1, 2)"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "wrong argument count" in result.stderr


def test_c_hosted_rustic_interpreter_rejects_runaway_while_loop_with_step_limit(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "while 1 { 1 }"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "step limit exceeded" in result.stderr


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
