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


def test_c_hosted_rustic_interpreter_evaluates_remainder_with_multiplicative_precedence(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    expectations = {
        "10 % 4 + 2 * 3": 8,
        "2 + 7 % 4 * 3": 11,
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


def test_c_hosted_rustic_interpreter_evaluates_division_with_multiplicative_precedence(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    expectations = {
        "20 / 5 + 3 * 2": 10,
        "18 / 3 % 4": 2,
        "2 + 24 / 3 / 2": 6,
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


def test_c_hosted_rustic_interpreter_rejects_division_by_zero(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "5 / 0"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "division by zero" in result.stderr


def test_c_hosted_rustic_interpreter_uses_remainder_in_recursive_divisibility_guard(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn even(n) { if n == 0 { 1 } else { if n % 2 == 0 { even(n - 2) } else { 0 } } }; even(8)"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 1\n"


def test_c_hosted_rustic_interpreter_rejects_remainder_by_zero(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "5 % 0"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "division by zero" in result.stderr


def test_c_hosted_rustic_interpreter_evaluates_boolean_negation(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    expectations = {
        "!0": 1,
        "!1": 0,
        "!(2 < 1)": 1,
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


def test_c_hosted_rustic_interpreter_evaluates_boolean_conjunction_and_disjunction(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    expectations = {
        "1 < 2 && 3 < 4": 1,
        "1 < 2 && 3 > 4": 0,
        "0 || 5 == 5": 1,
        "0 || 0": 0,
        "1 + 2 == 3 && 2 * 3 == 6": 1,
        "1 == 1 || 2 == 3 && missing": 1,
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


def test_c_hosted_rustic_interpreter_short_circuits_boolean_operators(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    expectations = {
        "0 && missing": 0,
        "1 || missing": 1,
        "0 && 1 / 0": 0,
        "1 || 1 / 0": 1,
        "0 && { missing }": 0,
        "1 || { missing }": 1,
        "0 && { missing } + 1": 0,
        "1 || if 0 { missing } else { 2 }": 1,
        "0 && (missing || 1)": 0,
        "0 && if if 1 { 0 } else { 1 } { missing } else { 2 }": 0,
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


def test_c_hosted_rustic_interpreter_uses_boolean_negation_in_recursive_guard(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn done(n) { if !(n == 0) { done(n - 1) } else { 9 } }; done(3)"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 9\n"


def test_c_hosted_rustic_interpreter_rejects_single_bang_without_operand(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "!"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "expected integer" in result.stderr


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


def test_c_hosted_rustic_interpreter_breaks_out_of_while_loop(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "let n = 0; let total = 0; while n < 10 { n = n + 1; if n == 4 { break; } else { total = total + n; } }; total"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 6\n"


def test_c_hosted_rustic_interpreter_continues_while_loop_iteration(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "let n = 0; let total = 0; while n < 5 { n = n + 1; if n == 3 { continue; } else { total = total + n; } }; total"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 12\n"


def test_c_hosted_rustic_interpreter_rejects_loop_control_outside_loop(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    for source in ("break;", "continue;"):
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert "loop control outside loop" in result.stderr


def test_c_hosted_rustic_interpreter_rejects_loop_control_in_while_condition(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    for source in (
        "while if 1 { break; } else { 1 } { 99 }",
        "while if 1 { continue; } else { 1 } { 99 }",
    ):
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert "loop control outside loop" in result.stderr


def test_c_hosted_rustic_interpreter_loop_control_stops_remaining_loop_body_statements(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    expectations = {
        "let n = 0; let x = 0; while n < 3 { n = n + 1; if n == 2 { continue; } else { 0 }; x = x + 10; }; x": 20,
        "let n = 0; let x = 0; while n < 3 { n = n + 1; if n == 2 { break; } else { 0 }; x = x + 10; }; x": 10,
    }
    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_loop_control_from_called_function(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    for source in (
        "fn stop() { break; }; while 1 { stop(); }",
        "fn skip() { continue; }; while 1 { skip(); }",
    ):
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert "loop control outside loop" in result.stderr


def test_c_hosted_rustic_interpreter_runs_loop_control_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_loop_control_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.split(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "let n = 0; let total = 0; while n < 10 { n = n + 1; if n == 4 { break; } else { total = total + n; } }; total",
            6,
        ),
        (
            "let n = 0; let total = 0; while n < 5 { n = n + 1; if n == 3 { continue; } else { total = total + n; } }; total",
            12,
        ),
        (
            "let n = 0; let x = 0; while n < 3 { n = n + 1; if n == 2 { continue; } else { 0 }; x = x + 10; }; x",
            20,
        ),
        (
            "let n = 0; let x = 0; while n < 3 { n = n + 1; if n == 2 { break; } else { 0 }; x = x + 10; }; x",
            10,
        ),
        (
            "let n = 0; let found = 0; while n < 8 { n = n + 1; if found == 1 { continue; } else { if n % 4 == 0 { found = n; break; } else { 0 } } }; found",
            4,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_match_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_match_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("let n = 2; match n { 1 => 10, 2 => 20, _ => 99 }", 20),
        ("let n = 3; match n { 1 => missing, 2 => 20, _ => n + 4 }", 7),
        ("let n = 4; match n % 3 { 0 => 30, 1 => 40, _ => 50 }", 40),
        (
            "let n = 0; while n < 5 { n = n + 1; match n { 3 => { continue; }, _ => 0 }; if n == 5 { break; } else { 0 } }; n",
            5,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_evaluates_array_literal_indexing(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    expectations = {
        "[1, 2 + 3, 9][1]": 5,
        "let xs = [3, 5, 8]; xs[0] + xs[2]": 11,
    }
    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_indexes_scoped_array_results(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "{ [42] }[0]": 42,
        "if 1 { [7] } else { [8] }[0]": 7,
        "fn arr() { [5] }; arr()[0]": 5,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_releases_outer_scope_while_condition_arrays(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    source = "let n = 0; let total = 0; while [1][0] && n < 65 { total = total + 1; n = n + 1; }; total"

    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 65\n"


def test_c_hosted_rustic_interpreter_preserves_arrays_assigned_to_outer_bindings(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = [0]; { xs = [7]; 0 }; xs[0]": 7,
        "let xs = [0]; while xs[0] < 3 { xs = [xs[0] + 1]; 0 }; xs[0]": 3,
        "let n = 0; let xs = [0]; while n < 65 { xs = [n]; n = n + 1; 0 }; xs[0]": 64,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_releases_block_scoped_arrays(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    source = "let n = 0; let total = 0; while n < 65 { let xs = [1]; total = total + xs[0]; n = n + 1; }; total"

    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 65\n"


def test_c_hosted_rustic_interpreter_releases_top_level_array_temporaries(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    let_statements = [f"let x{index} = [{index}][0]" for index in range(65)]
    expression_statements = [f"[{index}][0]" for index in range(65)]
    cases = [
        "; ".join(let_statements + ["x64"]),
        "; ".join(expression_statements),
    ]

    for source in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => 64\n"


def test_c_hosted_rustic_interpreter_preserves_array_under_construction(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "[[1][0], 2][1]": 2,
        "let xs = [[1][0], 2]; xs[1]": 2,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_array_index_out_of_bounds(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "[1, 2][2]"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "array index out of bounds" in result.stderr


def test_c_hosted_rustic_interpreter_reports_array_lengths(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "len([1, 2, 3])": 3,
        "let xs = [3, 5, 8]; len(xs) + xs[len(xs) - 1]": 11,
        "let n = 0; let total = 0; while n < len([1, 2, 3, 4]) { total = total + len([9, 8]); n = n + 1; }; total": 8,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_len_on_non_arrays(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    result = subprocess.run(
        [str(binary), "len(1)"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "expected array" in result.stderr


def test_c_hosted_rustic_interpreter_rebuilds_arrays_with_set_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = [1, 2, 3]; let ys = set(xs, 1, 9); xs[1] + ys[1]": 11,
        "let xs = [0, 0, 0]; let i = 0; while i < len(xs) { xs = set(xs, i, i + 1); i = i + 1; }; xs[0] + xs[1] + xs[2]": 6,
        "set([1, 2], 0, 9)[0]": 9,
        "let xs = [1, 2]; set(set(xs, 0, 7), 1, 8)[0] + set(set(xs, 0, 7), 1, 8)[1]": 15,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_set_helper_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "set(1, 0, 9)": "expected array",
        "set([1, 2], 2, 9)": "array index out of bounds",
        "set([1, 2], 0, [9])": "expected integer",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_appends_arrays_with_push_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = [1, 2]; let ys = push(xs, 3); len(xs) * 10 + len(ys) + ys[2]": 26,
        "let xs = []; let i = 0; while i < 4 { xs = push(xs, i + 1); i = i + 1; }; xs[0] + xs[1] + xs[2] + xs[3]": 10,
        "push([1], 2)[1]": 2,
        "let xs = [1]; push(push(xs, 2), 3)[2]": 3,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_push_helper_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    full_array = "[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]"
    cases = {
        "push(1, 2)": "expected array",
        "push([1], [2])": "expected integer",
        f"push({full_array}, 16)": "too many bindings",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_summarizes_arrays_with_sum_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "sum([1, 2, 3])": 6,
        "let xs = []; sum(xs)": 0,
        "let xs = []; let i = 0; while i < 4 { xs = push(xs, i + 1); i = i + 1; }; sum(xs)": 10,
        "sum(push([1, 2], 3)) + len(push([1, 2], 3))": 9,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_sum_helper_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "sum(1)": "expected array",
        "sum([1], [2])": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_counts_array_values(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "count([1, 2, 1, 3], 1)": 2,
        "count([], 9)": 0,
        "let xs = []; let i = 0; while i < 5 { xs = push(xs, i % 2); i = i + 1; }; count(xs, 1)": 2,
        "count(push([2, 3], 2), 2) + sum(push([2, 3], 2))": 9,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_count_helper_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "count(1, 1)": "expected array",
        "count([1], [1])": "expected integer",
        "count([1])": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_finds_array_minimum_and_maximum(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "min([3, 1, 4, 2])": 1,
        "max([3, 1, 4, 2])": 4,
        "let xs = []; let i = 0; while i < 5 { xs = push(xs, 10 - i * 2); i = i + 1; }; min(xs) * 10 + max(xs)": 30,
        "max(push([2, 9], 5)) - min(push([2, 9], 5))": 7,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_min_max_helper_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "min(1)": "expected array",
        "max(1)": "expected array",
        "min([])": "empty array",
        "max([])": "empty array",
        "min([1], [2])": "wrong argument count",
        "max([1], [2])": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_checks_array_membership_with_any_all_helpers(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "any([1, 2, 3], 2)": 1,
        "any([1, 2, 3], 9)": 0,
        "all([4, 4, 4], 4)": 1,
        "all([4, 5, 4], 4)": 0,
        "all([], 7) + any([], 7)": 1,
        "let xs = []; let i = 0; while i < 4 { xs = push(xs, i % 2); i = i + 1; }; any(xs, 1) * 10 + all(xs, 1)": 10,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_any_all_helper_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "any(1, 1)": "expected array",
        "all(1, 1)": "expected array",
        "any([1], [1])": "expected integer",
        "all([1], [1])": "expected integer",
        "any([1])": "wrong argument count",
        "all([1])": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_finds_array_values(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "find([4, 5, 4], 4)": 0,
        "find([4, 5, 4], 5)": 1,
        "find([4, 5, 4], 9)": -1,
        "find([], 9)": -1,
        "fn even(x) { x % 2 == 0 }; find(concat([9], filter([1, 2, 3, 4], even)), 4)": 2,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_checks_cross_array_membership(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "contains_any([1, 2, 3], [9, 2])": 1,
        "contains_any([1, 2, 3], [9, 8])": 0,
        "contains_any([], [1]) + contains_any([1], [])": 0,
        "fn even(x) { x % 2 == 0 }; contains_any(filter(range(6), even), concat([7], [5, 4]))": 1,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_search_helper_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "find(1, 1)": "expected array",
        "find([1], [1])": "expected integer",
        "find([1])": "wrong argument count",
        "contains_any(1, [1])": "expected array",
        "contains_any([1], 1)": "expected array",
        "contains_any([1])": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_releases_search_helper_temporaries(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    source = "let n = 0; let total = 0; while n < 65 { total = total + find(concat([9], [n % 3]), 2) + contains_any(concat([n], [7]), [7]); n = n + 1; }; total"

    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 42\n"


def test_c_hosted_rustic_interpreter_sorts_arrays(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "sort([3, 1, 2])[0] * 100 + sort([3, 1, 2])[2]": 103,
        "len(sort([]))": 0,
        "let xs = sort(concat([4, 1], [3, 2])); xs[0] * 1000 + xs[1] * 100 + xs[2] * 10 + xs[3]": 1234,
        "find(sort([5, 2, 5, 1]), 5)": 2,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_deduplicates_arrays(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = dedup([3, 1, 3, 2, 1]); len(xs) * 100 + sum(xs)": 306,
        "len(dedup([]))": 0,
        "contains_any(dedup([9, 9, 4]), [4])": 1,
        "let xs = dedup(sort([3, 1, 3, 2, 1])); xs[0] * 100 + xs[1] * 10 + xs[2]": 123,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_sort_dedup_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "sort(1)": "expected array",
        "sort([1], 2)": "wrong argument count",
        "dedup(1)": "expected array",
        "dedup([1], 2)": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_releases_sort_dedup_temporaries(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    source = "let n = 0; let total = 0; while n < 65 { total = total + sum(dedup(sort([3, 1, 3]))); n = n + 1; }; total"

    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 260\n"


def test_c_hosted_rustic_interpreter_builds_bounded_ranges(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "len(range(0))": 0,
        "sum(range(5))": 10,
        "range(4)[2]": 2,
        "let xs = range(6); len(xs) * 10 + xs[5]": 65,
        "sum(push(range(3), 9))": 12,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_range_helper_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "range([1])": "expected integer",
        "range(-1)": "expected integer",
        "range(17)": "too many bindings",
        "range(1, 2)": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_reverses_arrays_with_reverse_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "reverse([1, 2, 3])[0]": 3,
        "let xs = reverse(range(5)); len(xs) * 100 + xs[0] * 10 + xs[4]": 540,
        "sum(push(reverse([1, 2]), 9))": 12,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_takes_array_prefixes_with_take_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "sum(take(range(6), 3))": 3,
        "len(take([8, 9], 0))": 0,
        "let xs = take(reverse(range(6)), 4); len(xs) * 100 + xs[0] * 10 + xs[3]": 452,
        "sum(take(range(3), 9))": 3,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_drops_array_prefixes_with_drop_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "sum(drop(range(6), 3))": 12,
        "len(drop([8, 9], 2))": 0,
        "let xs = drop(reverse(range(6)), 2); len(xs) * 100 + xs[0] * 10 + xs[3]": 430,
        "sum(drop(range(3), 9))": 0,
        "sum(difference(drop([1, 2, 3, 4], 1), [3]))": 6,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_counts_partitions_with_callback_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "fn even(x) { x % 2 == 0 }; partition_count(range(7), even)": 4,
        "fn positive(x) { x > 0 }; partition_count([], positive)": 0,
        "fn keep(x) { x > 2 && x < 6 }; partition_count(difference(range(8), [4]), keep)": 2,
        "fn every(x) { 1 }; partition_count(drop([5, 6, 7], 1), every)": 2,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_sums_sliding_windows_with_window_sum_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "sum(window_sum(range(6), 3))": 30,
        "len(window_sum([8, 9], 3))": 0,
        "let xs = window_sum(take(range(6), 5), 2); len(xs) * 100 + xs[0] * 10 + xs[3]": 417,
        "sum(drop(window_sum(range(6), 2), 2))": 21,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_counts_fixed_size_chunks_with_chunk_count_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "chunk_count(range(6), 2)": 3,
        "chunk_count(range(5), 2)": 3,
        "chunk_count([], 3)": 0,
        "chunk_count(drop(range(7), 1), 4)": 2,
        "chunk_count(window_sum(range(6), 2), 3)": 2,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rotates_arrays_with_rotate_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "rotate([1, 2, 3, 4], 1)[0]": 2,
        "let xs = rotate(range(5), 2); len(xs) * 100 + xs[0] * 10 + xs[4]": 521,
        "sum(take(rotate(range(6), 4), 3))": 9,
        "len(rotate([], 3))": 0,
        "sum(rotate(range(4), 6))": 6,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_sums_fixed_size_chunks_with_chunk_sum_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = chunk_sum(range(7), 3); len(xs) * 100 + xs[0] * 10 + xs[2]": 336,
        "sum(chunk_sum([5, 6], 3))": 11,
        "len(chunk_sum([], 2))": 0,
        "sum(window_sum(chunk_sum(range(8), 2), 2))": 42,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rotates_arrays_right_with_rotate_right_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "rotate_right([1, 2, 3, 4], 1)[0]": 4,
        "let xs = rotate_right(range(5), 2); len(xs) * 100 + xs[0] * 10 + xs[4]": 532,
        "sum(take(rotate_right(range(6), 4), 3))": 9,
        "len(rotate_right([], 3))": 0,
        "sum(rotate_right(range(4), 6))": 6,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_builds_prefix_sums_with_prefix_sum_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = prefix_sum([2, 3, 5]); len(xs) * 100 + xs[0] * 10 + xs[2]": 330,
        "len(prefix_sum([]))": 0,
        "sum(window_sum(prefix_sum(range(5)), 2))": 30,
        "sum(chunk_sum(prefix_sum(rotate_right(range(6), 2)), 3))": 59,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_builds_adjacent_diffs_with_adjacent_diff_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = adjacent_diff([2, 5, 9]); len(xs) * 100 + xs[0] * 10 + xs[2]": 324,
        "len(adjacent_diff([]))": 0,
        "len(adjacent_diff([7]))": 1,
        "sum(adjacent_diff(prefix_sum([2, 3, 5, 7])))": 17,
        "sum(window_sum(adjacent_diff(rotate_right(range(6), 2)), 2))": 1,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_builds_moving_average_sums_with_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = moving_average_sum([2, 4, 8, 10], 2); len(xs) * 100 + xs[0] * 10 + xs[2]": 339,
        "len(moving_average_sum([], 3))": 0,
        "len(moving_average_sum([1, 2], 3))": 0,
        "sum(moving_average_sum(prefix_sum([2, 3, 5, 7]), 2))": 23,
        "sum(adjacent_diff(moving_average_sum(sort([8, 2, 4, 10]), 2)))": 9,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_finds_array_medians_with_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "median([7, 1, 5])": 5,
        "median([9, 1, 5, 3])": 4,
        "median(sort([8, 2, 4, 10]))": 6,
        "median(dedup([5, 1, 5, 9, 1]))": 5,
        "median(moving_average_sum([2, 4, 8, 10], 2))": 6,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_computes_array_variance_and_mode_helpers(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "variance_sum([1, 2, 3])": 2,
        "variance_sum([2, 4, 8, 10])": 40,
        "variance_sum(sort([9, 1, 5, 3]))": 36,
        "variance_sum(dedup([5, 1, 5, 9, 1]))": 32,
        "mode([3, 1, 3, 2])": 3,
        "mode([2, 1, 2, 1])": 1,
        "mode(sort([4, 2, 4, 2, 4]))": 4,
        "median([9, 1, 5]) + mode([2, 7, 2]) + variance_sum([1, 2, 3])": 9,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_computes_array_distribution_helpers(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "unique_count([3, 1, 3, 2, 1, 3])": 3,
        "unique_count([])": 0,
        "unique_count(sort([5, 1, 5, 9, 1])) + mode([2, 2, 7])": 5,
        "let xs = histogram_count([3, 1, 3, 2, 1, 3]); len(xs) * 100 + xs[0] * 10 + xs[2]": 323,
        "len(histogram_count([]))": 0,
        "sum(histogram_count(dedup([4, 2, 4, 1])))": 3,
        "max(histogram_count([2, 2, 1, 3, 3, 3])) + unique_count(dedup([7, 7, 8]))": 5,
        "let xs = histogram_values([3, 1, 3, 2, 1, 3]); len(xs) * 100 + xs[0] * 10 + xs[2]": 313,
        "len(histogram_values([]))": 0,
        "sum(histogram_values([3, 1, 3, 2, 1, 3])) + sum(histogram_count([3, 1, 3, 2, 1, 3]))": 12,
        "frequency_score([3, 1, 3, 2, 1, 3], 3)": 3,
        "frequency_score([], 3)": 0,
        "frequency_score(histogram_count([2, 2, 1, 3, 3, 3]), 1)": 1,
        "histogram_pairs_score(histogram_values([3, 1, 3, 2, 1, 3]), histogram_count([3, 1, 3, 2, 1, 3]))": 13,
        "histogram_pairs_score([], [])": 0,
        "histogram_pairs_score(histogram_values(clamp([9, 1, 5, 3], 2, 6)), histogram_count(clamp([9, 1, 5, 3], 2, 6)))": 16,
        "histogram_distance_score(histogram_values([3, 1, 3, 2]), histogram_count([3, 1, 3, 2]), [3, 2, 2])": 3,
        "histogram_distance_score(histogram_values([1]), histogram_count([1]), [2])": 2,
        "histogram_distance_score([], [], [1, 2, 3])": 3,
        "histogram_distance_score(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]), clamp([3, 3, 1, 9], 1, 3)) + histogram_pairs_score(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]))": 8,
        "fn square(x) { x * x }; weighted_score([1, 2, 3], square)": 14,
        "fn square(x) { x * x }; weighted_score([], square)": 0,
        "fn boost(x) { x + frequency_score([3, 1, 3], 3) }; weighted_score(histogram_values([3, 1, 3]), boost) + histogram_pairs_score(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]))": 15,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_computes_array_ranking_helpers(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "nth_sorted([9, 1, 5, 3], 0)": 1,
        "nth_sorted([9, 1, 5, 3], 2)": 5,
        "nth_sorted(dedup([4, 2, 4, 8, 2]), 2)": 8,
        "let xs = top_count([5, 1, 9, 3], 2); len(xs) * 100 + xs[0] * 10 + xs[1]": 295,
        "sum(top_count([5, 1, 9, 3], 3))": 17,
        "len(top_count([], 3))": 0,
        "len(top_count(range(4), 0))": 0,
        "sum(top_count(histogram_count([2, 2, 1, 3, 3, 3]), 2))": 5,
        "nth_sorted(histogram_values([3, 1, 3, 2, 1]), 1) + frequency_score([3, 1, 3, 2, 1], 1)": 4,
        "rank_of([9, 1, 5, 3], 5)": 2,
        "rank_of([9, 1, 5, 3], 7)": -1,
        "rank_of([], 7)": -1,
        "rank_of(histogram_values([3, 1, 3, 2, 1]), 2) + nth_sorted([9, 1, 5, 3], 1)": 4,
        "top_sum([5, 1, 9, 3], 2)": 14,
        "top_sum([5, 1, 9, 3], 8)": 18,
        "top_sum([], 3)": 0,
        "top_sum(histogram_count([2, 2, 1, 3, 3, 3]), 2) + rank_of([9, 1, 5, 3], 9)": 8,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_computes_array_clamp_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = clamp([5, 1, 9, 3], 3, 6); len(xs) * 1000 + xs[0] * 100 + xs[1] * 10 + xs[2]": 4536,
        "len(clamp([], 0, 3))": 0,
        "sum(clamp(range(7), 2, 4))": 21,
        "top_sum(clamp([9, 1, 5, 3], 2, 6), 2) + rank_of(clamp([9, 1, 5, 3], 2, 6), 5)": 13,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_computes_array_threshold_validation_helpers(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "threshold_count([1, 3, 5, 7], 3, 6)": 2,
        "threshold_count([], 0, 9)": 0,
        "threshold_all([3, 5, 6], 3, 6)": 1,
        "threshold_all([3, 8, 6], 3, 6)": 0,
        "threshold_all([], 3, 6)": 1,
        "outlier_count([1, 3, 5, 7], 3, 6)": 2,
        "outlier_count([], 3, 6)": 0,
        "threshold_window_count([3, 4, 5, 7, 3], 3, 6, 3)": 1,
        "threshold_window_count([3, 4], 3, 4, 3)": 0,
        "outlier_score([1, 3, 8, 5], 3, 6)": 4,
        "outlier_score([], 3, 6)": 0,
        "threshold_run_count([3, 4, 7, 3, 5, 9, 4], 3, 6)": 3,
        "threshold_run_count([], 3, 6)": 0,
        "outlier_streak([1, 3, 8, 9, 5, 10], 3, 6)": 2,
        "outlier_streak([], 3, 6)": 0,
        "threshold_run_score([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": 14,
        "threshold_run_score([], 3, 6)": 0,
        "outlier_run_count([1, 3, 8, 9, 5, 10], 3, 6)": 3,
        "outlier_run_count([], 3, 6)": 0,
        "let xs = threshold_run_lengths([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); len(xs) * 1000 + xs[0] * 100 + xs[1] * 10 + xs[2]": 3231,
        "len(threshold_run_lengths([], 3, 6))": 0,
        "let xs = outlier_run_lengths([1, 3, 8, 9, 5, 10], 3, 6); len(xs) * 1000 + xs[0] * 100 + xs[1] * 10 + xs[2]": 3121,
        "len(outlier_run_lengths([], 3, 6))": 0,
        "threshold_run_length_score([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": 14,
        "threshold_run_length_score([], 3, 6)": 0,
        "outlier_run_length_score([1, 3, 8, 9, 5, 10], 3, 6)": 6,
        "outlier_run_length_score([], 3, 6)": 0,
        "threshold_longest_run([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": 3,
        "threshold_longest_run([], 3, 6)": 0,
        "threshold_shortest_run([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": 1,
        "threshold_shortest_run([1, 7], 3, 6)": 0,
        "threshold_shortest_run([], 3, 6)": 0,
        "outlier_shortest_run([1, 3, 8, 9, 5, 10], 3, 6)": 1,
        "outlier_shortest_run([3, 4, 5], 3, 6)": 0,
        "outlier_shortest_run([], 3, 6)": 0,
        "outlier_longest_run([1, 3, 8, 9, 5, 10], 3, 6)": 2,
        "outlier_longest_run([3, 4, 5], 3, 6)": 0,
        "outlier_longest_run([], 3, 6)": 0,
        "threshold_run_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": 2,
        "threshold_run_delta([1, 7], 3, 6)": 0,
        "threshold_run_delta([], 3, 6)": 0,
        "outlier_run_delta([1, 3, 8, 9, 10, 5, 0], 3, 6)": 2,
        "outlier_run_delta([3, 4, 5], 3, 6)": 0,
        "outlier_run_delta([], 3, 6)": 0,
        "threshold_run_ratio_score([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": 3,
        "threshold_run_ratio_score([1, 7], 3, 6)": 0,
        "threshold_run_ratio_score([], 3, 6)": 0,
        "outlier_run_ratio_score([1, 3, 8, 9, 10, 5, 0], 3, 6)": 2,
        "outlier_run_ratio_score([3, 4, 5], 3, 6)": 0,
        "outlier_run_ratio_score([], 3, 6)": 0,
        "threshold_transition_count([3, 4, 7, 3, 5, 9, 4], 3, 6)": 4,
        "threshold_transition_count([3], 3, 6)": 0,
        "threshold_transition_count([], 3, 6)": 0,
        "outlier_transition_count([1, 3, 8, 9, 10, 5, 0], 3, 6)": 4,
        "outlier_transition_count([3, 4, 5], 3, 6)": 0,
        "outlier_transition_count([], 3, 6)": 0,
        "threshold_transition_score([3, 4, 7, 3, 5, 9, 4], 3, 6)": 7,
        "threshold_transition_score([3], 3, 6)": 0,
        "threshold_transition_score([], 3, 6)": 0,
        "outlier_transition_score([3, 4, 7, 3, 5, 9, 4], 3, 6)": 4,
        "outlier_transition_score([3, 4, 5], 3, 6)": 0,
        "outlier_transition_score([], 3, 6)": 0,
        "sum(threshold_run_lengths(clamp([9, 1, 5, 3], 2, 6), 2, 6)) + sum(outlier_run_lengths(clamp([9, 1, 5, 3], 2, 6), 3, 5))": 6,
        "threshold_run_length_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_length_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 20,
        "threshold_longest_run(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_shortest_run(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 6,
        "threshold_run_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6) + outlier_run_delta([1, 3, 8, 9, 10, 5, 0], 3, 6)": 4,
        "threshold_run_ratio_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_ratio_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 4,
        "threshold_transition_count(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_transition_count(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 1,
        "threshold_transition_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_transition_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 2,
        "threshold_all(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_count(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 3,
        "threshold_window_count(clamp([9, 1, 5, 3], 2, 6), 2, 6, 2) + outlier_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 5,
        "threshold_run_count(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_streak(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 3,
        "threshold_run_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_count(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 17,
        "threshold_count(clamp([9, 1, 5, 3], 2, 6), 2, 5) + weighted_score([1, 2], fn_boost)": 10,
        "histogram_within_distance(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]), [3, 1], 1)": 1,
        "histogram_within_distance(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]), [3], 0)": 0,
        "histogram_within_distance(histogram_values([]), histogram_count([]), [], 0)": 1,
        "histogram_within_distance(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]), clamp([3, 3, 1, 9], 1, 3), 1) + threshold_count(histogram_count([3, 1, 3]), 1, 2)": 3,
    }

    for source, expected in expectations.items():
        helper_prefix = "fn fn_boost(x) { x + 2 }; " if "fn_boost" in source else ""
        result = subprocess.run(
            [str(binary), f"{helper_prefix}{source}"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{helper_prefix}{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_split_partition_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_split_partition_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("sum(drop(range(6), 3))", 12),
        ("fn odd(x) { x % 2 == 1 }; partition_count(drop(range(8), 2), odd)", 3),
        ("sum(window_sum(take(range(7), 6), 3))", 30),
        (
            "fn keep(x) { x > 1 }; let xs = difference(drop([0, 1, 2, 3, 4], 1), [3]); partition_count(xs, keep) * 100 + sum(xs)",
            207,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_reshape_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_reshape_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("chunk_count(range(8), 3)", 3),
        ("let xs = rotate(drop(range(7), 2), 2); len(xs) * 100 + xs[0] * 10 + xs[4]", 543),
        ("sum(window_sum(rotate(take(range(8), 6), 3), 2))", 25),
        ("chunk_count(rotate(range(5), 4), 2) * 100 + sum(take(rotate(range(5), 1), 3))", 306),
        ("let xs = chunk_sum(range(8), 3); len(xs) * 100 + xs[0] * 10 + xs[2]", 343),
        ("sum(window_sum(rotate_right(chunk_sum(range(9), 2), 2), 2))", 50),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_statistics_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_statistics_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("let xs = prefix_sum(range(6)); len(xs) * 100 + xs[0] * 10 + xs[5]", 615),
        ("sum(window_sum(prefix_sum(range(5)), 2))", 30),
        ("sum(adjacent_diff(prefix_sum([2, 3, 5, 7])))", 17),
        ("sum(chunk_sum(adjacent_diff(rotate_right(range(6), 2)), 3))", 3),
        ("sum(moving_average_sum(prefix_sum([2, 3, 5, 7]), 2))", 23),
        ("sum(adjacent_diff(moving_average_sum(sort([8, 2, 4, 10]), 2)))", 9),
        ("median(sort([9, 1, 5, 3])) + median(dedup([5, 1, 5, 9, 1]))", 9),
        ("variance_sum(sort([9, 1, 5, 3])) + mode(dedup([2, 4, 2, 8, 4]))", 38),
        ("median(moving_average_sum([2, 4, 8, 10], 2)) + variance_sum([1, 2, 3]) + mode([6, 1, 6])", 14),
        ("unique_count(sort([5, 1, 5, 9, 1])) + max(histogram_count([2, 2, 1, 3, 3, 3]))", 6),
        ("sum(histogram_values([3, 1, 3, 2, 1, 3])) + frequency_score([3, 1, 3, 2, 1, 3], 1)", 8),
        ("histogram_pairs_score(histogram_values([3, 1, 3, 2, 1, 3]), histogram_count([3, 1, 3, 2, 1, 3]))", 13),
        ("histogram_distance_score(histogram_values([3, 1, 3, 2]), histogram_count([3, 1, 3, 2]), [3, 2, 2])", 3),
        ("histogram_within_distance(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]), [3, 1], 1)", 1),
        ("threshold_count(clamp([9, 1, 5, 3], 2, 6), 2, 5) + histogram_within_distance(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]), [3], 0)", 3),
        ("threshold_all(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_count(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 3),
        ("threshold_window_count(clamp([9, 1, 5, 3], 2, 6), 2, 6, 2) + outlier_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 5),
        ("threshold_run_count(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_streak(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 3),
        ("threshold_run_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_count(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 17),
        ("sum(threshold_run_lengths(clamp([9, 1, 5, 3], 2, 6), 2, 6)) + sum(outlier_run_lengths(clamp([9, 1, 5, 3], 2, 6), 3, 5))", 6),
        ("threshold_run_length_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_length_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 20),
        ("threshold_longest_run(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_shortest_run(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 6),
        ("threshold_shortest_run(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_longest_run(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 6),
        ("threshold_run_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6) + outlier_run_delta([1, 3, 8, 9, 10, 5, 0], 3, 6)", 4),
        ("threshold_run_ratio_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_ratio_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 4),
        ("threshold_transition_count(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_transition_count(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 1),
        ("threshold_transition_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_transition_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 2),
        ("fn square(x) { x * x }; weighted_score(histogram_values([3, 1, 3, 2, 1, 3]), square)", 14),
        ("nth_sorted(histogram_values([3, 1, 3, 2, 1]), 1) + frequency_score([3, 1, 3, 2, 1], 1)", 4),
        ("sum(top_count(histogram_count([2, 2, 1, 3, 3, 3]), 2)) + nth_sorted([9, 1, 5, 3], 2)", 10),
        ("rank_of(histogram_values([3, 1, 3, 2, 1]), 2) + top_sum(histogram_count([2, 2, 1, 3, 3, 3]), 2)", 6),
        ("sum(clamp([9, 1, 5, 3], 2, 6)) + top_sum(clamp(histogram_count([2, 2, 1, 3, 3, 3]), 1, 2), 2)", 20),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_reverse_take_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "reverse(1)": "expected array",
        "reverse([1], 2)": "wrong argument count",
        "take(1, 1)": "expected array",
        "take([1], [1])": "expected integer",
        "take([1], -1)": "expected integer",
        "take([1])": "wrong argument count",
        "drop(1, 1)": "expected array",
        "drop([1], [1])": "expected integer",
        "drop([1], -1)": "expected integer",
        "drop([1])": "wrong argument count",
        "window_sum(1, 1)": "expected array",
        "window_sum([1], [1])": "expected integer",
        "window_sum([1], 0)": "expected integer",
        "window_sum([1], -1)": "expected integer",
        "window_sum([1])": "wrong argument count",
        "chunk_count(1, 1)": "expected array",
        "chunk_count([1], [1])": "expected integer",
        "chunk_count([1], 0)": "expected integer",
        "chunk_count([1], -1)": "expected integer",
        "chunk_count([1])": "wrong argument count",
        "rotate(1, 1)": "expected array",
        "rotate([1], [1])": "expected integer",
        "rotate([1], -1)": "expected integer",
        "rotate([1])": "wrong argument count",
        "chunk_sum(1, 1)": "expected array",
        "chunk_sum([1], [1])": "expected integer",
        "chunk_sum([1], 0)": "expected integer",
        "chunk_sum([1], -1)": "expected integer",
        "chunk_sum([1])": "wrong argument count",
        "rotate_right(1, 1)": "expected array",
        "rotate_right([1], [1])": "expected integer",
        "rotate_right([1], -1)": "expected integer",
        "rotate_right([1])": "wrong argument count",
        "prefix_sum(1)": "expected array",
        "prefix_sum([1], 2)": "wrong argument count",
        "adjacent_diff(1)": "expected array",
        "adjacent_diff([1], 2)": "wrong argument count",
        "moving_average_sum(1, 1)": "expected array",
        "moving_average_sum([1], [1])": "expected integer",
        "moving_average_sum([1], 0)": "expected integer",
        "moving_average_sum([1], -1)": "expected integer",
        "moving_average_sum([1])": "wrong argument count",
        "median(1)": "expected array",
        "median([])": "empty array",
        "median([1], 2)": "wrong argument count",
        "variance_sum(1)": "expected array",
        "variance_sum([])": "empty array",
        "variance_sum([1], 2)": "wrong argument count",
        "mode(1)": "expected array",
        "mode([])": "empty array",
        "mode([1], 2)": "wrong argument count",
        "unique_count(1)": "expected array",
        "unique_count([1], 2)": "wrong argument count",
        "histogram_count(1)": "expected array",
        "histogram_count([1], 2)": "wrong argument count",
        "histogram_values(1)": "expected array",
        "histogram_values([1], 2)": "wrong argument count",
        "frequency_score(1, 1)": "expected array",
        "frequency_score([1], [1])": "expected integer",
        "frequency_score([1])": "wrong argument count",
        "histogram_pairs_score(1, [])": "expected array",
        "histogram_pairs_score([], 1)": "expected array",
        "histogram_pairs_score([1])": "wrong argument count",
        "histogram_pairs_score([1], [1, 2])": "array length mismatch",
        "histogram_distance_score(1, [], [])": "expected array",
        "histogram_distance_score([], 1, [])": "expected array",
        "histogram_distance_score([], [], 1)": "expected array",
        "histogram_distance_score([1], [1, 2], [])": "array length mismatch",
        "histogram_distance_score([1], [1])": "wrong argument count",
        "weighted_score(1, 1)": "expected array",
        "weighted_score([1], 1)": "undefined identifier",
        "fn add(x, y) { x + y }; weighted_score([1], add)": "wrong argument count",
        "fn returns_array(x) { [x] }; weighted_score([1], returns_array)": "expected integer",
        "weighted_score([1])": "wrong argument count",
        "nth_sorted(1, 0)": "expected array",
        "nth_sorted([1], [0])": "expected integer",
        "nth_sorted([1], -1)": "expected integer",
        "nth_sorted([], 0)": "empty array",
        "nth_sorted([1], 1)": "array index out of bounds",
        "nth_sorted([1])": "wrong argument count",
        "top_count(1, 1)": "expected array",
        "top_count([1], [1])": "expected integer",
        "top_count([1], -1)": "expected integer",
        "top_count([1])": "wrong argument count",
        "rank_of(1, 1)": "expected array",
        "rank_of([1], [1])": "expected integer",
        "rank_of([1])": "wrong argument count",
        "top_sum(1, 1)": "expected array",
        "top_sum([1], [1])": "expected integer",
        "top_sum([1], -1)": "expected integer",
        "top_sum([1])": "wrong argument count",
        "clamp(1, 0, 1)": "expected array",
        "clamp([1], [0], 1)": "expected integer",
        "clamp([1], 0, [1])": "expected integer",
        "clamp([1], 0)": "wrong argument count",
        "threshold_count(1, 0, 1)": "expected array",
        "threshold_count([1], [0], 1)": "expected integer",
        "threshold_count([1], 0, [1])": "expected integer",
        "threshold_count([1], 0)": "wrong argument count",
        "threshold_all(1, 0, 1)": "expected array",
        "threshold_all([1], [0], 1)": "expected integer",
        "threshold_all([1], 0, [1])": "expected integer",
        "threshold_all([1], 0)": "wrong argument count",
        "outlier_count(1, 0, 1)": "expected array",
        "outlier_count([1], [0], 1)": "expected integer",
        "outlier_count([1], 0, [1])": "expected integer",
        "outlier_count([1], 0)": "wrong argument count",
        "threshold_window_count(1, 0, 1, 1)": "expected array",
        "threshold_window_count([1], [0], 1, 1)": "expected integer",
        "threshold_window_count([1], 0, [1], 1)": "expected integer",
        "threshold_window_count([1], 0, 1, [1])": "expected integer",
        "threshold_window_count([1], 0, 1, 0)": "expected integer",
        "threshold_window_count([1], 0, 1, -1)": "expected integer",
        "threshold_window_count([1], 0, 1)": "wrong argument count",
        "outlier_score(1, 0, 1)": "expected array",
        "outlier_score([1], [0], 1)": "expected integer",
        "outlier_score([1], 0, [1])": "expected integer",
        "outlier_score([1], 0)": "wrong argument count",
        "threshold_run_count(1, 0, 1)": "expected array",
        "threshold_run_count([1], [0], 1)": "expected integer",
        "threshold_run_count([1], 0, [1])": "expected integer",
        "threshold_run_count([1], 0)": "wrong argument count",
        "outlier_streak(1, 0, 1)": "expected array",
        "outlier_streak([1], [0], 1)": "expected integer",
        "outlier_streak([1], 0, [1])": "expected integer",
        "outlier_streak([1], 0)": "wrong argument count",
        "threshold_run_score(1, 0, 1)": "expected array",
        "threshold_run_score([1], [0], 1)": "expected integer",
        "threshold_run_score([1], 0, [1])": "expected integer",
        "threshold_run_score([1], 0)": "wrong argument count",
        "outlier_run_count(1, 0, 1)": "expected array",
        "outlier_run_count([1], [0], 1)": "expected integer",
        "outlier_run_count([1], 0, [1])": "expected integer",
        "outlier_run_count([1], 0)": "wrong argument count",
        "threshold_run_lengths(1, 0, 1)": "expected array",
        "threshold_run_lengths([1], [0], 1)": "expected integer",
        "threshold_run_lengths([1], 0, [1])": "expected integer",
        "threshold_run_lengths([1], 0)": "wrong argument count",
        "outlier_run_lengths(1, 0, 1)": "expected array",
        "outlier_run_lengths([1], [0], 1)": "expected integer",
        "outlier_run_lengths([1], 0, [1])": "expected integer",
        "outlier_run_lengths([1], 0)": "wrong argument count",
        "threshold_run_length_score(1, 0, 1)": "expected array",
        "threshold_run_length_score([1], [0], 1)": "expected integer",
        "threshold_run_length_score([1], 0, [1])": "expected integer",
        "threshold_run_length_score([1], 0)": "wrong argument count",
        "outlier_run_length_score(1, 0, 1)": "expected array",
        "outlier_run_length_score([1], [0], 1)": "expected integer",
        "outlier_run_length_score([1], 0, [1])": "expected integer",
        "outlier_run_length_score([1], 0)": "wrong argument count",
        "threshold_longest_run(1, 0, 1)": "expected array",
        "threshold_longest_run([1], [0], 1)": "expected integer",
        "threshold_longest_run([1], 0, [1])": "expected integer",
        "threshold_longest_run([1], 0)": "wrong argument count",
        "threshold_shortest_run(1, 0, 1)": "expected array",
        "threshold_shortest_run([1], [0], 1)": "expected integer",
        "threshold_shortest_run([1], 0, [1])": "expected integer",
        "threshold_shortest_run([1], 0)": "wrong argument count",
        "outlier_shortest_run(1, 0, 1)": "expected array",
        "outlier_shortest_run([1], [0], 1)": "expected integer",
        "outlier_shortest_run([1], 0, [1])": "expected integer",
        "outlier_shortest_run([1], 0)": "wrong argument count",
        "outlier_longest_run(1, 0, 1)": "expected array",
        "outlier_longest_run([1], [0], 1)": "expected integer",
        "outlier_longest_run([1], 0, [1])": "expected integer",
        "outlier_longest_run([1], 0)": "wrong argument count",
        "threshold_run_delta(1, 0, 1)": "expected array",
        "threshold_run_delta([1], [0], 1)": "expected integer",
        "threshold_run_delta([1], 0, [1])": "expected integer",
        "threshold_run_delta([1], 0)": "wrong argument count",
        "outlier_run_delta(1, 0, 1)": "expected array",
        "outlier_run_delta([1], [0], 1)": "expected integer",
        "outlier_run_delta([1], 0, [1])": "expected integer",
        "outlier_run_delta([1], 0)": "wrong argument count",
        "threshold_run_ratio_score(1, 0, 1)": "expected array",
        "threshold_run_ratio_score([1], [0], 1)": "expected integer",
        "threshold_run_ratio_score([1], 0, [1])": "expected integer",
        "threshold_run_ratio_score([1], 0)": "wrong argument count",
        "outlier_run_ratio_score(1, 0, 1)": "expected array",
        "outlier_run_ratio_score([1], [0], 1)": "expected integer",
        "outlier_run_ratio_score([1], 0, [1])": "expected integer",
        "outlier_run_ratio_score([1], 0)": "wrong argument count",
        "threshold_transition_count(1, 0, 1)": "expected array",
        "threshold_transition_count([1], [0], 1)": "expected integer",
        "threshold_transition_count([1], 0, [1])": "expected integer",
        "threshold_transition_count([1], 0)": "wrong argument count",
        "outlier_transition_count(1, 0, 1)": "expected array",
        "outlier_transition_count([1], [0], 1)": "expected integer",
        "outlier_transition_count([1], 0, [1])": "expected integer",
        "outlier_transition_count([1], 0)": "wrong argument count",
        "threshold_transition_score(1, 0, 1)": "expected array",
        "threshold_transition_score([1], [0], 1)": "expected integer",
        "threshold_transition_score([1], 0, [1])": "expected integer",
        "threshold_transition_score([1], 0)": "wrong argument count",
        "outlier_transition_score(1, 0, 1)": "expected array",
        "outlier_transition_score([1], [0], 1)": "expected integer",
        "outlier_transition_score([1], 0, [1])": "expected integer",
        "outlier_transition_score([1], 0)": "wrong argument count",
        "histogram_within_distance(1, [], [], 0)": "expected array",
        "histogram_within_distance([], 1, [], 0)": "expected array",
        "histogram_within_distance([], [], 1, 0)": "expected array",
        "histogram_within_distance([1], [1, 2], [], 0)": "array length mismatch",
        "histogram_within_distance([], [], [], [0])": "expected integer",
        "histogram_within_distance([], [], [], -1)": "expected integer",
        "histogram_within_distance([], [], [])": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_releases_reverse_take_temporaries(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let n = 0; let total = 0; while n < 65 { total = total + reverse([1])[0]; n = n + 1; }; total": 65,
        "let n = 0; let total = 0; while n < 65 { total = total + len(take([1, 2], 1)); n = n + 1; }; total": 65,
        "let n = 0; let total = 0; while n < 65 { total = total + len(drop([1, 2], 1)); n = n + 1; }; total": 65,
        "let n = 0; let total = 0; while n < 65 { total = total + sum(window_sum([1, 2], 2)); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + chunk_count([1, 2, 3], 2); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + rotate([1, 2], 1)[0]; n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + sum(chunk_sum([1, 2, 3], 2)); n = n + 1; }; total": 390,
        "let n = 0; let total = 0; while n < 65 { total = total + rotate_right([1, 2], 1)[0]; n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + prefix_sum([1, 2])[1]; n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + adjacent_diff([1, 3])[1]; n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + moving_average_sum([1, 3], 2)[0]; n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + median(sort([3, 1, 2])); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + variance_sum(sort([3, 1, 2])); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + mode(sort([3, 1, 3])); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + unique_count(sort([3, 1, 3])); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + sum(histogram_count([3, 1, 3])); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + sum(histogram_values([3, 1, 3])); n = n + 1; }; total": 260,
        "let n = 0; let total = 0; while n < 65 { total = total + frequency_score([3, 1, 3], 3); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + histogram_pairs_score(histogram_values([3, 1, 3]), histogram_count([3, 1, 3])); n = n + 1; }; total": 455,
        "let n = 0; let total = 0; while n < 65 { total = total + histogram_distance_score(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]), [3, 1]); n = n + 1; }; total": 65,
        "fn square(x) { x * x }; let n = 0; let total = 0; while n < 65 { total = total + weighted_score([1, 2], square); n = n + 1; }; total": 325,
        "let n = 0; let total = 0; while n < 65 { total = total + nth_sorted([3, 1, 2], 1); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + top_count([3, 1, 2], 2)[0]; n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + rank_of([3, 1, 2], 3); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + top_sum([3, 1, 2], 2); n = n + 1; }; total": 325,
        "let n = 0; let total = 0; while n < 65 { total = total + sum(clamp([3, 1, 5], 2, 4)); n = n + 1; }; total": 585,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_count(clamp([3, 1, 5], 2, 4), 2, 4); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_all(clamp([3, 1, 5], 2, 4), 2, 4); n = n + 1; }; total": 65,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_count(clamp([3, 1, 5], 2, 4), 3, 3); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_window_count(clamp([3, 1, 5], 2, 4), 2, 4, 2); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_score(clamp([3, 1, 5], 2, 4), 3, 3); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_count(clamp([3, 1, 5], 2, 4), 2, 4); n = n + 1; }; total": 65,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_streak(clamp([3, 1, 5], 2, 4), 3, 3); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_score(clamp([3, 1, 5], 2, 4), 2, 4); n = n + 1; }; total": 585,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_count(clamp([3, 1, 5], 2, 4), 3, 3); n = n + 1; }; total": 65,
        "let n = 0; let total = 0; while n < 65 { total = total + sum(threshold_run_lengths(clamp([3, 1, 5], 2, 4), 2, 4)); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + sum(outlier_run_lengths(clamp([3, 1, 5], 2, 4), 3, 3)); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_length_score(clamp([3, 1, 5], 2, 4), 2, 4); n = n + 1; }; total": 585,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_length_score(clamp([3, 1, 5], 2, 4), 3, 3); n = n + 1; }; total": 260,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_longest_run(clamp([3, 1, 5], 2, 4), 2, 4); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_shortest_run(clamp([3, 1, 5], 2, 4), 3, 3); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_shortest_run(clamp([3, 1, 5], 2, 4), 2, 4); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_longest_run(clamp([3, 1, 5], 2, 4), 3, 3); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_delta([1, 3, 8, 9, 10, 5, 0], 3, 6); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_ratio_score([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_ratio_score([1, 3, 8, 9, 10, 5, 0], 3, 6); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_transition_count([3, 4, 7, 3, 5, 9, 4], 3, 6); n = n + 1; }; total": 260,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_transition_count([1, 3, 8, 9, 10, 5, 0], 3, 6); n = n + 1; }; total": 260,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_transition_score([3, 4, 7, 3, 5, 9, 4], 3, 6); n = n + 1; }; total": 455,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_transition_score([3, 4, 7, 3, 5, 9, 4], 3, 6); n = n + 1; }; total": 260,
        "let n = 0; let total = 0; while n < 65 { total = total + histogram_within_distance(histogram_values([3, 1, 3]), histogram_count([3, 1, 3]), [3, 1], 1); n = n + 1; }; total": 65,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_ordering_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_ordering_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("let xs = reverse(range(6)); len(xs) * 100 + xs[0] * 10 + xs[5]", 650),
        (
            "fn odd(x) { x % 2 == 1 }; let xs = take(reverse(filter(range(10), odd)), 3); len(xs) * 100 + sum(xs)",
            321,
        ),
        (
            "fn shift(x) { x + 1 }; let xs = reverse(map(take(range(5), 4), shift)); xs[0] * 100 + xs[3]",
            401,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_transforms_arrays_with_map_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "fn double(x) { x * 2 }; sum(map([1, 2, 3], double))": 12,
        "fn inc(x) { x + 1 }; map(range(4), inc)[3]": 4,
        "fn square(x) { x * x }; let xs = map(range(5), square); len(xs) * 100 + sum(xs)": 530,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_filters_arrays_with_filter_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "fn even(x) { x % 2 == 0 }; sum(filter(range(7), even))": 12,
        "fn keep(x) { x > 2 && x < 6 }; let xs = filter(range(8), keep); len(xs) * 100 + sum(xs)": 312,
        "fn none(x) { x > 9 }; len(filter(range(4), none))": 0,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_transforms_arrays_with_indexed_map_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "fn offset(i, x) { i * 10 + x }; sum(map_indexed([5, 6, 7], offset))": 48,
        "fn pairish(i, x) { i * 100 + x }; map_indexed(range(4), pairish)[3]": 303,
        "fn weight(i, x) { (i + 1) * x }; let xs = map_indexed([3, 4, 5], weight); len(xs) * 100 + sum(xs)": 326,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_filters_arrays_with_indexed_filter_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "fn odd_index(i, x) { i % 2 == 1 }; sum(filter_indexed([10, 20, 30, 40], odd_index))": 60,
        "fn keep(i, x) { i < 3 && x > 1 }; let xs = filter_indexed([0, 2, 4, 6], keep); len(xs) * 100 + sum(xs)": 206,
        "fn none(i, x) { i > 9 }; len(filter_indexed(range(4), none))": 0,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_map_filter_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "fn id(x) { x }; map(1, id)": "expected array",
        "fn id(x) { x }; filter(1, id)": "expected array",
        "fn id(x) { x }; partition_count(1, id)": "expected array",
        "fn both(i, x) { x }; map_indexed(1, both)": "expected array",
        "fn both(i, x) { x }; filter_indexed(1, both)": "expected array",
        "map([1], 1)": "undefined identifier",
        "filter([1], 1)": "undefined identifier",
        "partition_count([1], 1)": "undefined identifier",
        "map_indexed([1], 1)": "undefined identifier",
        "filter_indexed([1], 1)": "undefined identifier",
        "fn bad(x, y) { x }; map([1], bad)": "wrong argument count",
        "fn bad(x, y) { x }; filter([1], bad)": "wrong argument count",
        "fn bad(x, y) { x }; partition_count([1], bad)": "wrong argument count",
        "fn bad(x) { x }; map_indexed([1], bad)": "wrong argument count",
        "fn bad(x) { x }; filter_indexed([1], bad)": "wrong argument count",
        "fn bad(x) { [x] }; map([1], bad)": "expected integer",
        "fn bad(i, x) { [x] }; map_indexed([1], bad)": "expected integer",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_releases_map_filter_temporaries(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "fn id(x) { x }; let n = 0; let total = 0; while n < 65 { total = total + sum(map([1], id)); n = n + 1; }; total": 65,
        "fn yes(x) { 1 }; let n = 0; let total = 0; while n < 65 { total = total + len(filter([1], yes)); n = n + 1; }; total": 65,
        "fn yes(x) { 1 }; let n = 0; let total = 0; while n < 65 { total = total + partition_count([1], yes); n = n + 1; }; total": 65,
        "fn plus_index(i, x) { i + x }; let n = 0; let total = 0; while n < 65 { total = total + sum(map_indexed([1], plus_index)); n = n + 1; }; total": 65,
        "fn yes(i, x) { i == 0 && x == 1 }; let n = 0; let total = 0; while n < 65 { total = total + len(filter_indexed([1], yes)); n = n + 1; }; total": 65,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_indexed_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_indexed_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("fn weight(i, x) { (i + 1) * x }; sum(map_indexed([3, 4, 5], weight))", 26),
        ("fn odd_index(i, x) { i % 2 == 1 }; sum(filter_indexed([10, 20, 30, 40], odd_index))", 60),
        (
            "fn pairish(i, x) { i * 10 + x }; fn odd_index(i, x) { i % 2 == 1 }; fn add(acc, x) { acc + x }; fold(filter_indexed(map_indexed(range(6), pairish), odd_index), 0, add)",
            99,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_zips_arrays_with_binary_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "fn add(x, y) { x + y }; sum(zip_with([1, 2, 3], [10, 20, 30], add))": 66,
        "fn pairish(x, y) { x * 100 + y }; zip_with([1, 2, 3], [4, 5], pairish)[1]": 205,
        "fn product(x, y) { x * y }; let xs = zip_with(range(4), reverse(range(4)), product); len(xs) * 100 + sum(xs)": 404,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_repeats_integer_values(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "sum(repeat(4, 3))": 12,
        "len(repeat(9, 0))": 0,
        "fn add(x, y) { x + y }; sum(zip_with(repeat(2, 4), range(4), add))": 14,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_concatenates_arrays(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = concat([1, 2], [3, 4]); len(xs) * 100 + sum(xs)": 410,
        "concat([], [7, 8])[1]": 8,
        "fn add(acc, x) { acc + x }; fold(concat(take(range(5), 2), repeat(5, 3)), 0, add)": 16,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_repeat_concat_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "repeat([1], 2)": "expected integer",
        "repeat(1, [2])": "expected integer",
        "repeat(1, -1)": "expected integer",
        "repeat(1, 17)": "too many bindings",
        "repeat(1)": "wrong argument count",
        "concat(1, [2])": "expected array",
        "concat([1], 2)": "expected array",
        "concat(range(9), range(8))": "too many bindings",
        "concat([1])": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_releases_repeat_concat_temporaries(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    source = "let n = 0; let total = 0; while n < 65 { total = total + sum(concat(repeat(1, 2), [3])); n = n + 1; }; total"

    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 325\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_zip_with_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "fn add(x, y) { x + y }; zip_with(1, [2], add)": "expected array",
        "fn add(x, y) { x + y }; zip_with([1], 2, add)": "expected array",
        "zip_with([1], [2], 1)": "undefined identifier",
        "fn bad(x) { x }; zip_with([1], [2], bad)": "wrong argument count",
        "fn bad(x, y) { [x] }; zip_with([1], [2], bad)": "expected integer",
        "fn add(x, y) { x + y }; zip_with([1], [2])": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_releases_zip_with_temporaries(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    source = "fn add(x, y) { x + y }; let n = 0; let total = 0; while n < 65 { total = total + sum(zip_with([1], [2], add)); n = n + 1; }; total"

    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 195\n"


def test_c_hosted_rustic_interpreter_runs_array_zip_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_zip_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("fn add(x, y) { x + y }; sum(zip_with([1, 2, 3], [10, 20, 30], add))", 66),
        (
            "fn weight(i, x) { (i + 1) * x }; fn add(x, y) { x + y }; fn total(acc, x) { acc + x }; fold(zip_with(map_indexed(range(5), weight), filter_indexed([10, 11, 12, 13, 14], weight), add), 0, total)",
            100,
        ),
        (
            "fn product(x, y) { x * y }; let xs = zip_with(take(range(5), 3), reverse(range(5)), product); len(xs) * 100 + sum(xs)",
            307,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_repeat_concat_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_repeat_concat_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("sum(repeat(4, 3))", 12),
        ("fn add(x, y) { x + y }; sum(zip_with(repeat(2, 4), range(4), add))", 14),
        (
            "let xs = concat(repeat(7, 2), take(range(5), 3)); len(xs) * 100 + sum(xs)",
            517,
        ),
        (
            "fn add(acc, x) { acc + x }; fold(concat(take(range(5), 2), repeat(5, 3)), 0, add)",
            16,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_search_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_search_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("find([4, 5, 4], 5)", 1),
        (
            "fn even(x) { x % 2 == 0 }; find(concat([9], filter([1, 2, 3, 4], even)), 4)",
            2,
        ),
        ("contains_any([1, 2, 3], [9, 2])", 1),
        (
            "fn even(x) { x % 2 == 0 }; contains_any(filter(range(6), even), concat([7], [5, 4]))",
            1,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_compares_arrays_with_equals_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "equals([1, 2, 3], [1, 2, 3])": 1,
        "equals([1, 2], [1, 2, 3])": 0,
        "equals([1, 2, 4], [1, 2, 3])": 0,
        "equals([], [])": 1,
        "equals(sort([3, 1, 2]), dedup(sort([1, 2, 2, 3])))": 1,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_counts_array_intersections(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "intersection_count([1, 2, 3], [9, 2, 3])": 2,
        "intersection_count([1, 1, 2, 3], [1, 3, 3])": 2,
        "intersection_count([], [1, 2])": 0,
        "intersection_count(dedup(sort([3, 1, 3, 2])), dedup(sort([2, 4, 1])))": 2,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_builds_array_differences(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "let xs = difference([1, 2, 3, 2], [2, 9]); len(xs) * 100 + sum(xs)": 204,
        "len(difference([], [1, 2]))": 0,
        "let xs = difference(dedup(sort([4, 1, 4, 2, 3])), [2, 9]); xs[0] * 100 + xs[1] * 10 + xs[2]": 134,
        "sum(push(difference([1, 2, 3], [2]), 9))": 13,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_compares_array_prefixes_with_starts_with_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "starts_with([1, 2, 3], [1, 2])": 1,
        "starts_with([1, 2], [1, 2, 3])": 0,
        "starts_with([1, 9, 3], [1, 2])": 0,
        "starts_with([4, 5], [])": 1,
        "starts_with(dedup(sort([3, 1, 3, 2])), [1, 2])": 1,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_array_comparison_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "equals(1, [1])": "expected array",
        "equals([1], 1)": "expected array",
        "equals([1])": "wrong argument count",
        "starts_with(1, [1])": "expected array",
        "starts_with([1], 1)": "expected array",
        "starts_with([1])": "wrong argument count",
        "intersection_count(1, [1])": "expected array",
        "intersection_count([1], 1)": "expected array",
        "intersection_count([1])": "wrong argument count",
        "difference(1, [1])": "expected array",
        "difference([1], 1)": "expected array",
        "difference([1])": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_releases_array_comparison_temporaries(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    source = "let n = 0; let total = 0; while n < 65 { total = total + equals(sort([2, 1]), [1, 2]) + starts_with(dedup([1, 1, 2]), [1]) + intersection_count([1, 2, 3], [2, 3]) + len(difference([1, 2, 3], [2])); n = n + 1; }; total"

    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 390\n"


def test_c_hosted_rustic_interpreter_runs_array_order_compare_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_order_compare_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "let xs = sort([4, 1, 3, 2]); xs[0] * 1000 + xs[1] * 100 + xs[2] * 10 + xs[3]",
            1234,
        ),
        ("let xs = dedup([5, 2, 5, 3, 2]); len(xs) * 100 + sum(xs)", 310),
        (
            "let xs = dedup(sort(concat([3, 1, 3], [2, 1]))); xs[0] * 100 + xs[1] * 10 + xs[2]",
            123,
        ),
        ("contains_any(dedup(sort([8, 4, 8, 2])), [4]) + find(sort([7, 1, 7]), 7)", 2),
        ("equals(sort([3, 1, 2]), dedup(sort([1, 2, 2, 3])))", 1),
        ("starts_with(dedup(sort([4, 2, 4, 1])), [1, 2])", 1),
        ("intersection_count(dedup(sort([4, 1, 4, 2])), [2, 4, 8])", 2),
        (
            "let xs = difference(dedup(sort(concat([4, 1, 2], [4, 3]))), [2, 9]); xs[0] * 100 + xs[1] * 10 + xs[2]",
            134,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_folds_arrays_with_accumulator_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    expectations = {
        "fn add(acc, x) { acc + x }; fold([1, 2, 3], 0, add)": 6,
        "fn step(acc, x) { acc * 10 + x }; fold(range(4), 1, step)": 10123,
        "fn keep_even_total(acc, x) { if x % 2 == 0 { acc + x } else { acc } }; fold(range(7), 0, keep_even_total)": 12,
    }

    for source, expected in expectations.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_rejects_invalid_fold_arguments(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    cases = {
        "fn add(acc, x) { acc + x }; fold(1, 0, add)": "expected array",
        "fn add(acc, x) { acc + x }; fold([1], [0], add)": "expected integer",
        "fold([1], 0, 1)": "undefined identifier",
        "fn bad(x) { x }; fold([1], 0, bad)": "wrong argument count",
        "fn bad(acc, x) { [x] }; fold([1], 0, bad)": "expected integer",
        "fn add(acc, x) { acc + x }; fold([1], 0)": "wrong argument count",
    }

    for source, expected_error in cases.items():
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 2
        assert result.stdout == ""
        assert expected_error in result.stderr


def test_c_hosted_rustic_interpreter_releases_fold_temporaries(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    source = "fn add(acc, x) { acc + x }; let n = 0; let total = 0; while n < 65 { total = total + fold([1], 0, add); n = n + 1; }; total"

    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 65\n"


def test_c_hosted_rustic_interpreter_runs_array_fold_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_fold_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("fn add(acc, x) { acc + x }; fold(range(6), 0, add)", 15),
        (
            "fn odd(x) { x % 2 == 1 }; fn add_square(acc, x) { acc + x * x }; fold(filter(range(8), odd), 0, add_square)",
            84,
        ),
        (
            "fn step(acc, x) { acc * 10 + x }; fold(take(reverse(range(6)), 4), 0, step)",
            5432,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_transform_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_transform_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("fn double(x) { x * 2 }; sum(map(range(6), double))", 30),
        (
            "fn odd(x) { x % 2 == 1 }; fn square(x) { x * x }; sum(map(filter(range(8), odd), square))",
            84,
        ),
        (
            "fn small(x) { x < 4 }; fn shift(x) { x + 10 }; let xs = map(filter(range(7), small), shift); len(xs) * 100 + min(xs) * 10 + max(xs)",
            513,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_range_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_range_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        ("let xs = range(5); sum(xs) * 10 + len(xs)", 105),
        (
            "let xs = range(8); let i = 0; let evens = []; while i < len(xs) { if xs[i] % 2 == 0 { evens = push(evens, xs[i]) } else { 0 }; i = i + 1; }; sum(evens)",
            12,
        ),
        (
            "fn odds(n) { let xs = range(n); let out = []; let i = 0; while i < len(xs) { if xs[i] % 2 == 1 { out = push(out, xs[i]) } else { 0 }; i = i + 1; }; out }; count(odds(7), 3) * 10 + sum(odds(7))",
            19,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_any_all_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_any_all_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "let xs = []; let i = 0; while i < 6 { xs = push(xs, i % 3); i = i + 1; }; any(xs, 2) * 10 + all(xs, 2)",
            10,
        ),
        (
            "let xs = [1, 1, 1]; let ys = set(xs, 1, 2); all(xs, 1) * 10 + any(ys, 2)",
            11,
        ),
        (
            "fn build(n) { let xs = []; let i = 0; while i < n { xs = push(xs, i % 2); i = i + 1; }; xs }; any(build(5), 1) + all(build(5), 0)",
            1,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_min_max_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_min_max_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "let xs = []; let i = 0; while i < 5 { xs = push(xs, 10 - i * 2); i = i + 1; }; min(xs) * 10 + max(xs)",
            30,
        ),
        (
            "let xs = [3, 1, 4]; let ys = set(xs, 1, 6); min(xs) * 10 + max(ys)",
            16,
        ),
        (
            "fn build(n) { let xs = []; let i = 1; while i <= n { xs = push(xs, i * i); i = i + 1; }; xs }; max(build(4)) - min(build(4))",
            15,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_count_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_count_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "let xs = []; let i = 0; while i < 6 { xs = push(xs, i % 3); i = i + 1; }; count(xs, 2)",
            2,
        ),
        (
            "let xs = [1, 1, 2, 3]; let ys = set(xs, 2, 1); count(xs, 1) * 10 + count(ys, 1)",
            23,
        ),
        (
            "fn build(n) { let xs = []; let i = 0; while i < n { xs = push(xs, i % 2); i = i + 1; }; xs }; count(build(5), 0)",
            3,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_sum_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_sum_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "let xs = []; let i = 0; while i < 5 { xs = push(xs, i); i = i + 1; }; sum(xs)",
            10,
        ),
        (
            "let xs = [3, 1, 4]; let ys = set(xs, 1, 2); sum(xs) * 10 + sum(ys)",
            89,
        ),
        (
            "fn build(n) { let xs = []; let i = 1; while i <= n { xs = push(xs, i); i = i + 1; }; xs }; sum(build(4))",
            10,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_array_push_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_array_push_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.rsplit(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "let xs = []; let i = 0; while i < 4 { xs = push(xs, i + 1); i = i + 1; }; xs[0] + xs[1] + xs[2] + xs[3]",
            10,
        ),
        (
            "let xs = [2, 4]; let ys = push(xs, len(xs) + 4); len(xs) * 10 + len(ys) + ys[2]",
            29,
        ),
        (
            "let xs = [1]; push(push(xs, 2), 3)[0] + push(push(xs, 2), 3)[1] + push(push(xs, 2), 3)[2]",
            6,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_loop_arithmetic_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_loop_arithmetic_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.split(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "let n = 1; let total = 0; while n <= 10 { if n % 3 == 0 { total = total + n } else { 0 }; n = n + 1; }; total",
            18,
        ),
        (
            "let n = 96; let steps = 0; while n > 1 { n = n / 2; steps = steps + 1; }; steps",
            6,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_boolean_guards_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_boolean_guards_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.split(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "let n = 1; let total = 0; while n <= 10 { if n % 2 == 0 && n % 3 == 0 { total = total + n } else { 0 }; n = n + 1; }; total",
            6,
        ),
        (
            "fn limit(n) { if n < 0 || n > 10 { 0 } else { n } }; limit(7) + limit(12)",
            7,
        ),
        (
            "let x = 1; if x == 1 || missing { x } else { 0 }",
            1,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


def test_c_hosted_rustic_interpreter_runs_comparison_loop_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_comparison_loop_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.split(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "let n = 1; let score = 0; while n <= 8 { { fn in_range(x) { x >= 3 && x <= 6 }; if in_range(n) && n != 5 { score = score + n } else { 0 } }; n = n + 1; }; score",
            13,
        ),
        (
            "let n = 1; let total = 0; while n <= 7 { { fn is_edge(x) { x < 3 || x > 5 }; let keep = is_edge; if keep(n) { total = total + n } else { 0 } }; n = n + 1; }; total",
            16,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


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


def test_c_hosted_rustic_interpreter_runs_recursive_arithmetic_showcase_fixture(tmp_path):
    binary = compile_rustic_driver(tmp_path)
    fixture = ROOT / "tests" / "fixtures" / "rustic_recursive_arithmetic_showcase.txt"

    cases = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        source, expected_text = line.split(" => ", 1)
        cases.append((source, int(expected_text)))

    assert cases == [
        (
            "fn triangle(n) { if n == 0 { 0 } else { n + triangle(n - 1) } }; triangle(5)",
            15,
        ),
        (
            "fn factorial(n) { if n == 0 { 1 } else { n * factorial(n - 1) } }; factorial(5)",
            120,
        ),
    ]
    for source, expected in cases:
        result = subprocess.run(
            [str(binary), source],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{source} => {expected}\n"


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


def test_c_hosted_rustic_interpreter_evaluates_block_local_function(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "{ let factor = 3; fn scale(x) { x * factor }; scale(4) }"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 12\n"


def test_c_hosted_rustic_interpreter_keeps_block_local_functions_scoped(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "{ fn hidden() { 4 }; hidden() }; hidden()"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "undefined identifier" in result.stderr


def test_c_hosted_rustic_interpreter_calls_function_value_bound_with_let(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn inc(x) { x + 1 }; let f = inc; f(4)"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 5\n"


def test_c_hosted_rustic_interpreter_calls_function_value_returned_from_helper(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn inc(x) { x + 1 }; fn choose() { inc }; let f = choose(); f(6)"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 7\n"


def test_c_hosted_rustic_interpreter_rejects_integer_that_matches_function_value_encoding(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn inc(x) { x + 1 }; let f = 0 - 9223372036854775807 - 1; f(4)"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "undefined identifier" in result.stderr


def test_c_hosted_rustic_interpreter_rejects_stale_block_function_value_after_slot_reuse(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "let f = { fn hidden() { 1 }; hidden }; fn later() { 9 }; f()"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "undefined identifier" in result.stderr


def test_c_hosted_rustic_interpreter_calls_local_function_value_before_same_named_function(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "fn add() { 1 }; fn inc() { 2 }; let add = inc; add()"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{source} => 2\n"


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


def test_c_hosted_rustic_interpreter_evaluates_match_expression_arms(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "let n = 2; match n { 1 => 10, 2 => 20, _ => 99 }"
    result = subprocess.run(
        [str(binary), source],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.stdout == f"{source} => 20\n"
    assert result.stderr == ""


def test_c_hosted_rustic_interpreter_match_default_skips_unselected_arms(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "let n = 3; match n { 1 => missing, 2 => 20, _ => n + 4 }"
    result = subprocess.run(
        [str(binary), source],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.stdout == f"{source} => 7\n"
    assert result.stderr == ""


def test_c_hosted_rustic_interpreter_rejects_match_without_matching_default(tmp_path):
    binary = compile_rustic_driver(tmp_path)

    source = "match 3 { 1 => 10, 2 => 20 }"
    result = subprocess.run(
        [str(binary), source],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "no matching match arm" in result.stderr


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
