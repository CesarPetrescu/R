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
        "threshold_transition_density([3, 4, 7, 3, 5, 9, 4], 3, 6)": 1,
        "threshold_transition_density([3], 3, 6)": 0,
        "threshold_transition_density([], 3, 6)": 0,
        "outlier_transition_density([3, 4, 7, 3, 5, 9, 4], 3, 6)": 2,
        "outlier_transition_density([3, 4, 5], 3, 6)": 0,
        "outlier_transition_density([], 3, 6)": 0,
        "threshold_transition_balance([3, 4, 7, 3, 5, 9, 4], 3, 6)": -1,
        "threshold_transition_balance([7, 8], 3, 6)": 0,
        "threshold_transition_balance([3], 3, 6)": 0,
        "threshold_transition_balance([], 3, 6)": 0,
        "outlier_transition_balance([3, 4, 7, 3, 5, 9, 4], 3, 6)": 2,
        "outlier_transition_balance([3, 4, 5], 3, 6)": 0,
        "outlier_transition_balance([7], 3, 6)": 0,
        "outlier_transition_balance([], 3, 6)": 0,
        "threshold_run_contrast([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": 5,
        "threshold_run_contrast([7, 8], 3, 6)": 0,
        "threshold_run_contrast([3], 3, 6)": 0,
        "threshold_run_contrast([], 3, 6)": 0,
        "outlier_run_contrast([1, 3, 8, 9, 10, 5, 0], 3, 6)": 3,
        "outlier_run_contrast([3, 4, 5], 3, 6)": 0,
        "outlier_run_contrast([7], 3, 6)": 0,
        "outlier_run_contrast([], 3, 6)": 0,
        "threshold_run_contrast_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": 3,
        "threshold_run_contrast_delta([7, 8], 3, 6)": 0,
        "threshold_run_contrast_delta([3], 3, 6)": 0,
        "threshold_run_contrast_delta([], 3, 6)": 0,
        "outlier_run_contrast_delta([1, 3, 8, 9, 10, 5, 0], 3, 6)": 1,
        "outlier_run_contrast_delta([3, 4, 5], 3, 6)": 0,
        "outlier_run_contrast_delta([7], 3, 6)": 0,
        "outlier_run_contrast_delta([], 3, 6)": 0,
        "threshold_run_signal_score([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": 6,
        "threshold_run_signal_score([7, 8], 3, 6)": 0,
        "threshold_run_signal_score([3], 3, 6)": 0,
        "threshold_run_signal_score([], 3, 6)": 0,
        "outlier_run_signal_score([1, 3, 8, 9, 10, 5, 0], 3, 6)": 3,
        "outlier_run_signal_score([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_score([7], 3, 6)": 0,
        "outlier_run_signal_score([], 3, 6)": 0,
        "threshold_run_signal_density([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": 1,
        "threshold_run_signal_density([7, 8], 3, 6)": 0,
        "threshold_run_signal_density([3], 3, 6)": 0,
        "threshold_run_signal_density([], 3, 6)": 0,
        "outlier_run_signal_density([1, 8, 9, 3, 0, 1], 3, 6)": 1,
        "outlier_run_signal_density([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density([7], 3, 6)": 0,
        "outlier_run_signal_density([], 3, 6)": 0,
        "threshold_run_signal_density_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1,
        "threshold_run_signal_density_delta([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_delta([3], 3, 6)": 0,
        "threshold_run_signal_density_delta([], 3, 6)": 0,
        "outlier_run_signal_density_delta([1, 8, 9, 3, 0, 1], 3, 6)": 0,
        "outlier_run_signal_density_delta([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_delta([7], 3, 6)": 0,
        "outlier_run_signal_density_delta([], 3, 6)": 0,
        "threshold_run_signal_density_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -4,
        "threshold_run_signal_density_ratio([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_ratio([3], 3, 6)": 0,
        "threshold_run_signal_density_ratio([], 3, 6)": 0,
        "outlier_run_signal_density_ratio([1, 8, 9, 3, 0, 1], 3, 6)": -2,
        "outlier_run_signal_density_ratio([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_ratio([7], 3, 6)": 0,
        "outlier_run_signal_density_ratio([], 3, 6)": 0,
        "threshold_run_signal_density_gap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -2,
        "threshold_run_signal_density_gap([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_gap([3], 3, 6)": 0,
        "threshold_run_signal_density_gap([], 3, 6)": 0,
        "outlier_run_signal_density_gap([1, 8, 9, 3, 0, 1], 3, 6)": 0,
        "outlier_run_signal_density_gap([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_gap([7], 3, 6)": 0,
        "outlier_run_signal_density_gap([], 3, 6)": 0,
        "threshold_run_signal_density_band([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -6,
        "threshold_run_signal_density_band([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band([3], 3, 6)": 0,
        "threshold_run_signal_density_band([], 3, 6)": 0,
        "outlier_run_signal_density_band([1, 8, 9, 3, 0, 1], 3, 6)": -5,
        "outlier_run_signal_density_band([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band([7], 3, 6)": 0,
        "outlier_run_signal_density_band([], 3, 6)": 0,
        "threshold_run_signal_density_band_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -9,
        "threshold_run_signal_density_band_ratio([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_ratio([3], 3, 6)": 0,
        "threshold_run_signal_density_band_ratio([], 3, 6)": 0,
        "outlier_run_signal_density_band_ratio([1, 8, 9, 3, 0, 1], 3, 6)": -7,
        "outlier_run_signal_density_band_ratio([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_ratio([7], 3, 6)": 0,
        "outlier_run_signal_density_band_ratio([], 3, 6)": 0,
        "threshold_run_signal_density_band_gap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -7,
        "threshold_run_signal_density_band_gap([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_gap([3], 3, 6)": 0,
        "threshold_run_signal_density_band_gap([], 3, 6)": 0,
        "outlier_run_signal_density_band_gap([1, 8, 9, 3, 0, 1], 3, 6)": -5,
        "outlier_run_signal_density_band_gap([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_gap([7], 3, 6)": 0,
        "outlier_run_signal_density_band_gap([], 3, 6)": 0,
        "threshold_run_signal_density_band_gap_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -10,
        "threshold_run_signal_density_band_gap_ratio([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_gap_ratio([3], 3, 6)": 0,
        "threshold_run_signal_density_band_gap_ratio([], 3, 6)": 0,
        "outlier_run_signal_density_band_gap_ratio([1, 8, 9, 3, 0, 1], 3, 6)": -7,
        "outlier_run_signal_density_band_gap_ratio([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_gap_ratio([7], 3, 6)": 0,
        "outlier_run_signal_density_band_gap_ratio([], 3, 6)": 0,
        "threshold_run_signal_density_band_span([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -14,
        "threshold_run_signal_density_band_span([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span([], 3, 6)": 0,
        "outlier_run_signal_density_band_span([1, 8, 9, 3, 0, 1], 3, 6)": -12,
        "outlier_run_signal_density_band_span([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -17,
        "threshold_run_signal_density_band_span_ratio([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_ratio([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_ratio([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_ratio([1, 8, 9, 3, 0, 1], 3, 6)": -14,
        "outlier_run_signal_density_band_span_ratio([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_ratio([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_ratio([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -15,
        "threshold_run_signal_density_band_span_gap([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap([1, 8, 9, 3, 0, 1], 3, 6)": -12,
        "outlier_run_signal_density_band_span_gap([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -18,
        "threshold_run_signal_density_band_span_gap_ratio([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_ratio([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_ratio([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_ratio([1, 8, 9, 3, 0, 1], 3, 6)": -14,
        "outlier_run_signal_density_band_span_gap_ratio([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_ratio([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_ratio([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -20,
        "threshold_run_signal_density_band_span_gap_delta([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta([1, 8, 9, 3, 0, 1], 3, 6)": -15,
        "outlier_run_signal_density_band_span_gap_delta([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -23,
        "threshold_run_signal_density_band_span_gap_delta_ratio([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_ratio([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_ratio([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_ratio([1, 8, 9, 3, 0, 1], 3, 6)": -17,
        "outlier_run_signal_density_band_span_gap_delta_ratio([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_ratio([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_ratio([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -21,
        "threshold_run_signal_density_band_span_gap_delta_balance([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance([1, 8, 9, 3, 0, 1], 3, 6)": -15,
        "outlier_run_signal_density_band_span_gap_delta_balance([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -24,
        "threshold_run_signal_density_band_span_gap_delta_balance_ratio([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ratio([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ratio([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ratio([1, 8, 9, 3, 0, 1], 3, 6)": -17,
        "outlier_run_signal_density_band_span_gap_delta_balance_ratio([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ratio([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ratio([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -26,
        "threshold_run_signal_density_band_span_gap_delta_balance_delta([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_delta([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_delta([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_delta([1, 8, 9, 3, 0, 1], 3, 6)": -18,
        "outlier_run_signal_density_band_span_gap_delta_balance_delta([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_delta([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_delta([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_count([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -29,
        "threshold_run_signal_density_band_span_gap_delta_balance_count([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_count([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_count([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_count([1, 8, 9, 3, 0, 1], 3, 6)": -20,
        "outlier_run_signal_density_band_span_gap_delta_balance_count([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_count([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_count([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_drift([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -33,
        "threshold_run_signal_density_band_span_gap_delta_balance_drift([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_drift([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_drift([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_drift([1, 8, 9, 3, 0, 1], 3, 6)": -22,
        "outlier_run_signal_density_band_span_gap_delta_balance_drift([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_drift([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_drift([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spread([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -37,
        "threshold_run_signal_density_band_span_gap_delta_balance_spread([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spread([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spread([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spread([1, 8, 9, 3, 0, 1], 3, 6)": -27,
        "outlier_run_signal_density_band_span_gap_delta_balance_spread([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spread([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spread([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mass([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -43,
        "threshold_run_signal_density_band_span_gap_delta_balance_mass([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mass([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mass([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mass([1, 8, 9, 3, 0, 1], 3, 6)": -32,
        "outlier_run_signal_density_band_span_gap_delta_balance_mass([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mass([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mass([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_load([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -46,
        "threshold_run_signal_density_band_span_gap_delta_balance_load([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_load([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_load([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_load([1, 8, 9, 3, 0, 1], 3, 6)": -35,
        "outlier_run_signal_density_band_span_gap_delta_balance_load([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_load([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_load([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flux([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -50,
        "threshold_run_signal_density_band_span_gap_delta_balance_flux([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flux([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flux([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flux([1, 8, 9, 3, 0, 1], 3, 6)": -37,
        "outlier_run_signal_density_band_span_gap_delta_balance_flux([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flux([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flux([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wave([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -53,
        "threshold_run_signal_density_band_span_gap_delta_balance_wave([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wave([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wave([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wave([1, 8, 9, 3, 0, 1], 3, 6)": -43,
        "outlier_run_signal_density_band_span_gap_delta_balance_wave([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wave([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wave([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_peak([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -56,
        "threshold_run_signal_density_band_span_gap_delta_balance_peak([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_peak([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_peak([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_peak([1, 8, 9, 3, 0, 1], 3, 6)": -46,
        "outlier_run_signal_density_band_span_gap_delta_balance_peak([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_peak([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_peak([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tail([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -57,
        "threshold_run_signal_density_band_span_gap_delta_balance_tail([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tail([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tail([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tail([1, 8, 9, 3, 0, 1], 3, 6)": -48,
        "outlier_run_signal_density_band_span_gap_delta_balance_tail([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tail([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tail([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_edge([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -61,
        "threshold_run_signal_density_band_span_gap_delta_balance_edge([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_edge([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_edge([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_edge([1, 8, 9, 3, 0, 1], 3, 6)": -53,
        "outlier_run_signal_density_band_span_gap_delta_balance_edge([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_edge([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_edge([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rim([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -64,
        "threshold_run_signal_density_band_span_gap_delta_balance_rim([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rim([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rim([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rim([1, 8, 9, 3, 0, 1], 3, 6)": -55,
        "outlier_run_signal_density_band_span_gap_delta_balance_rim([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rim([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rim([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lip([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -68,
        "threshold_run_signal_density_band_span_gap_delta_balance_lip([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lip([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lip([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lip([1, 8, 9, 3, 0, 1], 3, 6)": -57,
        "outlier_run_signal_density_band_span_gap_delta_balance_lip([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lip([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lip([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jaw([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -77,
        "threshold_run_signal_density_band_span_gap_delta_balance_jaw([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jaw([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jaw([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jaw([1, 8, 9, 3, 0, 1], 3, 6)": -64,
        "outlier_run_signal_density_band_span_gap_delta_balance_jaw([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jaw([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jaw([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bite([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -85,
        "threshold_run_signal_density_band_span_gap_delta_balance_bite([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bite([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bite([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bite([1, 8, 9, 3, 0, 1], 3, 6)": -71,
        "outlier_run_signal_density_band_span_gap_delta_balance_bite([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bite([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bite([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_grip([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -91,
        "threshold_run_signal_density_band_span_gap_delta_balance_grip([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_grip([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_grip([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_grip([1, 8, 9, 3, 0, 1], 3, 6)": -76,
        "outlier_run_signal_density_band_span_gap_delta_balance_grip([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_grip([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_grip([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_hold([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -100,
        "threshold_run_signal_density_band_span_gap_delta_balance_hold([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_hold([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_hold([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_hold([1, 8, 9, 3, 0, 1], 3, 6)": -84,
        "outlier_run_signal_density_band_span_gap_delta_balance_hold([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_hold([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_hold([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lock([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -107,
        "threshold_run_signal_density_band_span_gap_delta_balance_lock([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lock([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lock([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lock([1, 8, 9, 3, 0, 1], 3, 6)": -88,
        "outlier_run_signal_density_band_span_gap_delta_balance_lock([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lock([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lock([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_seal([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -117,
        "threshold_run_signal_density_band_span_gap_delta_balance_seal([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_seal([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_seal([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_seal([1, 8, 9, 3, 0, 1], 3, 6)": -95,
        "outlier_run_signal_density_band_span_gap_delta_balance_seal([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_seal([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_seal([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mark([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -129,
        "threshold_run_signal_density_band_span_gap_delta_balance_mark([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mark([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mark([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mark([1, 8, 9, 3, 0, 1], 3, 6)": -105,
        "outlier_run_signal_density_band_span_gap_delta_balance_mark([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mark([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mark([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stamp([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -136,
        "threshold_run_signal_density_band_span_gap_delta_balance_stamp([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stamp([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stamp([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stamp([1, 8, 9, 3, 0, 1], 3, 6)": -110,
        "outlier_run_signal_density_band_span_gap_delta_balance_stamp([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stamp([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stamp([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_press([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -141,
        "threshold_run_signal_density_band_span_gap_delta_balance_press([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_press([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_press([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_press([1, 8, 9, 3, 0, 1], 3, 6)": -114,
        "outlier_run_signal_density_band_span_gap_delta_balance_press([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_press([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_press([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pin([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -145,
        "threshold_run_signal_density_band_span_gap_delta_balance_pin([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pin([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pin([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pin([1, 8, 9, 3, 0, 1], 3, 6)": -118,
        "outlier_run_signal_density_band_span_gap_delta_balance_pin([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pin([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pin([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_snap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -152,
        "threshold_run_signal_density_band_span_gap_delta_balance_snap([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_snap([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_snap([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_snap([1, 8, 9, 3, 0, 1], 3, 6)": -122,
        "outlier_run_signal_density_band_span_gap_delta_balance_snap([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_snap([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_snap([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_clasp([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -162,
        "threshold_run_signal_density_band_span_gap_delta_balance_clasp([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_clasp([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_clasp([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_clasp([1, 8, 9, 3, 0, 1], 3, 6)": -132,
        "outlier_run_signal_density_band_span_gap_delta_balance_clasp([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_clasp([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_clasp([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_latch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -169,
        "threshold_run_signal_density_band_span_gap_delta_balance_latch([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_latch([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_latch([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_latch([1, 8, 9, 3, 0, 1], 3, 6)": -136,
        "outlier_run_signal_density_band_span_gap_delta_balance_latch([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_latch([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_latch([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_hook([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -176,
        "threshold_run_signal_density_band_span_gap_delta_balance_hook([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_hook([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_hook([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_hook([1, 8, 9, 3, 0, 1], 3, 6)": -141,
        "outlier_run_signal_density_band_span_gap_delta_balance_hook([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_hook([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_hook([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_link([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -181,
        "threshold_run_signal_density_band_span_gap_delta_balance_link([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_link([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_link([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_link([1, 8, 9, 3, 0, 1], 3, 6)": -145,
        "outlier_run_signal_density_band_span_gap_delta_balance_link([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_link([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_link([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_chain([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -191,
        "threshold_run_signal_density_band_span_gap_delta_balance_chain([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_chain([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_chain([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_chain([1, 8, 9, 3, 0, 1], 3, 6)": -152,
        "outlier_run_signal_density_band_span_gap_delta_balance_chain([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_chain([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_chain([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rope([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -199,
        "threshold_run_signal_density_band_span_gap_delta_balance_rope([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rope([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rope([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rope([1, 8, 9, 3, 0, 1], 3, 6)": -159,
        "outlier_run_signal_density_band_span_gap_delta_balance_rope([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rope([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rope([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_knot([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -205,
        "threshold_run_signal_density_band_span_gap_delta_balance_knot([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_knot([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_knot([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_knot([1, 8, 9, 3, 0, 1], 3, 6)": -164,
        "outlier_run_signal_density_band_span_gap_delta_balance_knot([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_knot([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_knot([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tie([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -212,
        "threshold_run_signal_density_band_span_gap_delta_balance_tie([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tie([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tie([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tie([1, 8, 9, 3, 0, 1], 3, 6)": -168,
        "outlier_run_signal_density_band_span_gap_delta_balance_tie([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tie([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tie([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bow([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -218,
        "threshold_run_signal_density_band_span_gap_delta_balance_bow([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bow([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bow([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bow([1, 8, 9, 3, 0, 1], 3, 6)": -173,
        "outlier_run_signal_density_band_span_gap_delta_balance_bow([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bow([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bow([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_arc([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -223,
        "threshold_run_signal_density_band_span_gap_delta_balance_arc([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_arc([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_arc([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_arc([1, 8, 9, 3, 0, 1], 3, 6)": -177,
        "outlier_run_signal_density_band_span_gap_delta_balance_arc([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_arc([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_arc([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_arch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -231,
        "threshold_run_signal_density_band_span_gap_delta_balance_arch([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_arch([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_arch([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_arch([1, 8, 9, 3, 0, 1], 3, 6)": -184,
        "outlier_run_signal_density_band_span_gap_delta_balance_arch([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_arch([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_arch([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gate([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -244,
        "threshold_run_signal_density_band_span_gap_delta_balance_gate([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gate([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gate([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gate([1, 8, 9, 3, 0, 1], 3, 6)": -193,
        "outlier_run_signal_density_band_span_gap_delta_balance_gate([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gate([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gate([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_guard([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -254,
        "threshold_run_signal_density_band_span_gap_delta_balance_guard([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_guard([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_guard([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_guard([1, 8, 9, 3, 0, 1], 3, 6)": -200,
        "outlier_run_signal_density_band_span_gap_delta_balance_guard([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_guard([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_guard([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shield([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -260,
        "threshold_run_signal_density_band_span_gap_delta_balance_shield([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shield([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shield([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shield([1, 8, 9, 3, 0, 1], 3, 6)": -205,
        "outlier_run_signal_density_band_span_gap_delta_balance_shield([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shield([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shield([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wall([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -264,
        "threshold_run_signal_density_band_span_gap_delta_balance_wall([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wall([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wall([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wall([1, 8, 9, 3, 0, 1], 3, 6)": -207,
        "outlier_run_signal_density_band_span_gap_delta_balance_wall([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wall([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wall([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fort([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -274,
        "threshold_run_signal_density_band_span_gap_delta_balance_fort([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fort([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fort([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fort([1, 8, 9, 3, 0, 1], 3, 6)": -214,
        "outlier_run_signal_density_band_span_gap_delta_balance_fort([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fort([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fort([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_keep([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -277,
        "threshold_run_signal_density_band_span_gap_delta_balance_keep([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_keep([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_keep([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_keep([1, 8, 9, 3, 0, 1], 3, 6)": -217,
        "outlier_run_signal_density_band_span_gap_delta_balance_keep([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_keep([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_keep([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_core([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -290,
        "threshold_run_signal_density_band_span_gap_delta_balance_core([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_core([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_core([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_core([1, 8, 9, 3, 0, 1], 3, 6)": -227,
        "outlier_run_signal_density_band_span_gap_delta_balance_core([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_core([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_core([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_root([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -297,
        "threshold_run_signal_density_band_span_gap_delta_balance_root([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_root([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_root([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_root([1, 8, 9, 3, 0, 1], 3, 6)": -234,
        "outlier_run_signal_density_band_span_gap_delta_balance_root([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_root([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_root([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_crown([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -307,
        "threshold_run_signal_density_band_span_gap_delta_balance_crown([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_crown([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_crown([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_crown([1, 8, 9, 3, 0, 1], 3, 6)": -241,
        "outlier_run_signal_density_band_span_gap_delta_balance_crown([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_crown([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_crown([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_halo([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -314,
        "threshold_run_signal_density_band_span_gap_delta_balance_halo([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_halo([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_halo([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_halo([1, 8, 9, 3, 0, 1], 3, 6)": -246,
        "outlier_run_signal_density_band_span_gap_delta_balance_halo([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_halo([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_halo([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_crest([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -321,
        "threshold_run_signal_density_band_span_gap_delta_balance_crest([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_crest([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_crest([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_crest([1, 8, 9, 3, 0, 1], 3, 6)": -251,
        "outlier_run_signal_density_band_span_gap_delta_balance_crest([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_crest([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_crest([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_plume([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -326,
        "threshold_run_signal_density_band_span_gap_delta_balance_plume([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_plume([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_plume([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_plume([1, 8, 9, 3, 0, 1], 3, 6)": -255,
        "outlier_run_signal_density_band_span_gap_delta_balance_plume([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_plume([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_plume([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spire([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -333,
        "threshold_run_signal_density_band_span_gap_delta_balance_spire([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spire([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spire([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spire([1, 8, 9, 3, 0, 1], 3, 6)": -259,
        "outlier_run_signal_density_band_span_gap_delta_balance_spire([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spire([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spire([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flare([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -343,
        "threshold_run_signal_density_band_span_gap_delta_balance_flare([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flare([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flare([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flare([1, 8, 9, 3, 0, 1], 3, 6)": -266,
        "outlier_run_signal_density_band_span_gap_delta_balance_flare([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flare([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flare([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spark([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -349,
        "threshold_run_signal_density_band_span_gap_delta_balance_spark([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spark([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spark([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spark([1, 8, 9, 3, 0, 1], 3, 6)": -271,
        "outlier_run_signal_density_band_span_gap_delta_balance_spark([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spark([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spark([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_torch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -356,
        "threshold_run_signal_density_band_span_gap_delta_balance_torch([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_torch([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_torch([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_torch([1, 8, 9, 3, 0, 1], 3, 6)": -276,
        "outlier_run_signal_density_band_span_gap_delta_balance_torch([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_torch([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_torch([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ember([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -363,
        "threshold_run_signal_density_band_span_gap_delta_balance_ember([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ember([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ember([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ember([1, 8, 9, 3, 0, 1], 3, 6)": -283,
        "outlier_run_signal_density_band_span_gap_delta_balance_ember([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ember([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ember([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_glow([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -369,
        "threshold_run_signal_density_band_span_gap_delta_balance_glow([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_glow([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_glow([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_glow([1, 8, 9, 3, 0, 1], 3, 6)": -288,
        "outlier_run_signal_density_band_span_gap_delta_balance_glow([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_glow([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_glow([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ash([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -374,
        "threshold_run_signal_density_band_span_gap_delta_balance_ash([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ash([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ash([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ash([1, 8, 9, 3, 0, 1], 3, 6)": -292,
        "outlier_run_signal_density_band_span_gap_delta_balance_ash([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ash([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ash([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_blaze([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -381,
        "threshold_run_signal_density_band_span_gap_delta_balance_blaze([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_blaze([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_blaze([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_blaze([1, 8, 9, 3, 0, 1], 3, 6)": -297,
        "outlier_run_signal_density_band_span_gap_delta_balance_blaze([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_blaze([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_blaze([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flame([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -390,
        "threshold_run_signal_density_band_span_gap_delta_balance_flame([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flame([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flame([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flame([1, 8, 9, 3, 0, 1], 3, 6)": -305,
        "outlier_run_signal_density_band_span_gap_delta_balance_flame([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flame([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flame([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_smoke([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -397,
        "threshold_run_signal_density_band_span_gap_delta_balance_smoke([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_smoke([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_smoke([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_smoke([1, 8, 9, 3, 0, 1], 3, 6)": -309,
        "outlier_run_signal_density_band_span_gap_delta_balance_smoke([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_smoke([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_smoke([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stone([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -406,
        "threshold_run_signal_density_band_span_gap_delta_balance_stone([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stone([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stone([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stone([1, 8, 9, 3, 0, 1], 3, 6)": -316,
        "outlier_run_signal_density_band_span_gap_delta_balance_stone([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stone([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stone([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_brand([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -416,
        "threshold_run_signal_density_band_span_gap_delta_balance_brand([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_brand([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_brand([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_brand([1, 8, 9, 3, 0, 1], 3, 6)": -323,
        "outlier_run_signal_density_band_span_gap_delta_balance_brand([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_brand([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_brand([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_forge([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -425,
        "threshold_run_signal_density_band_span_gap_delta_balance_forge([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_forge([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_forge([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_forge([1, 8, 9, 3, 0, 1], 3, 6)": -331,
        "outlier_run_signal_density_band_span_gap_delta_balance_forge([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_forge([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_forge([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_anvil([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -426,
        "threshold_run_signal_density_band_span_gap_delta_balance_anvil([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_anvil([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_anvil([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_anvil([1, 8, 9, 3, 0, 1], 3, 6)": -333,
        "outlier_run_signal_density_band_span_gap_delta_balance_anvil([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_anvil([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_anvil([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_metal([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -433,
        "threshold_run_signal_density_band_span_gap_delta_balance_metal([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_metal([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_metal([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_metal([1, 8, 9, 3, 0, 1], 3, 6)": -340,
        "outlier_run_signal_density_band_span_gap_delta_balance_metal([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_metal([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_metal([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_iron([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -437,
        "threshold_run_signal_density_band_span_gap_delta_balance_iron([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_iron([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_iron([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_iron([1, 8, 9, 3, 0, 1], 3, 6)": -345,
        "outlier_run_signal_density_band_span_gap_delta_balance_iron([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_iron([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_iron([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mold([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -447,
        "threshold_run_signal_density_band_span_gap_delta_balance_mold([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mold([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mold([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mold([1, 8, 9, 3, 0, 1], 3, 6)": -355,
        "outlier_run_signal_density_band_span_gap_delta_balance_mold([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mold([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mold([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cast([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -457,
        "threshold_run_signal_density_band_span_gap_delta_balance_cast([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cast([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cast([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cast([1, 8, 9, 3, 0, 1], 3, 6)": -362,
        "outlier_run_signal_density_band_span_gap_delta_balance_cast([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cast([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cast([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ore([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -464,
        "threshold_run_signal_density_band_span_gap_delta_balance_ore([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ore([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ore([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ore([1, 8, 9, 3, 0, 1], 3, 6)": -367,
        "outlier_run_signal_density_band_span_gap_delta_balance_ore([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ore([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ore([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ingot([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -477,
        "threshold_run_signal_density_band_span_gap_delta_balance_ingot([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ingot([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ingot([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ingot([1, 8, 9, 3, 0, 1], 3, 6)": -377,
        "outlier_run_signal_density_band_span_gap_delta_balance_ingot([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ingot([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ingot([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_steel([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -478,
        "threshold_run_signal_density_band_span_gap_delta_balance_steel([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_steel([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_steel([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_steel([1, 8, 9, 3, 0, 1], 3, 6)": -379,
        "outlier_run_signal_density_band_span_gap_delta_balance_steel([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_steel([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_steel([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_smelt([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -484,
        "threshold_run_signal_density_band_span_gap_delta_balance_smelt([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_smelt([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_smelt([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_smelt([1, 8, 9, 3, 0, 1], 3, 6)": -384,
        "outlier_run_signal_density_band_span_gap_delta_balance_smelt([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_smelt([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_smelt([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_alloy([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -489,
        "threshold_run_signal_density_band_span_gap_delta_balance_alloy([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_alloy([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_alloy([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_alloy([1, 8, 9, 3, 0, 1], 3, 6)": -388,
        "outlier_run_signal_density_band_span_gap_delta_balance_alloy([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_alloy([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_alloy([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fuse([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -499,
        "threshold_run_signal_density_band_span_gap_delta_balance_fuse([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fuse([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fuse([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fuse([1, 8, 9, 3, 0, 1], 3, 6)": -395,
        "outlier_run_signal_density_band_span_gap_delta_balance_fuse([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fuse([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fuse([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_braze([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -503,
        "threshold_run_signal_density_band_span_gap_delta_balance_braze([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_braze([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_braze([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_braze([1, 8, 9, 3, 0, 1], 3, 6)": -400,
        "outlier_run_signal_density_band_span_gap_delta_balance_braze([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_braze([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_braze([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_meld([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -512,
        "threshold_run_signal_density_band_span_gap_delta_balance_meld([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_meld([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_meld([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_meld([1, 8, 9, 3, 0, 1], 3, 6)": -407,
        "outlier_run_signal_density_band_span_gap_delta_balance_meld([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_meld([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_meld([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_weld([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -522,
        "threshold_run_signal_density_band_span_gap_delta_balance_weld([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_weld([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_weld([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_weld([1, 8, 9, 3, 0, 1], 3, 6)": -414,
        "outlier_run_signal_density_band_span_gap_delta_balance_weld([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_weld([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_weld([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_solder([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -527,
        "threshold_run_signal_density_band_span_gap_delta_balance_solder([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_solder([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_solder([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_solder([1, 8, 9, 3, 0, 1], 3, 6)": -418,
        "outlier_run_signal_density_band_span_gap_delta_balance_solder([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_solder([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_solder([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rivet([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -536,
        "threshold_run_signal_density_band_span_gap_delta_balance_rivet([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rivet([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rivet([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rivet([1, 8, 9, 3, 0, 1], 3, 6)": -426,
        "outlier_run_signal_density_band_span_gap_delta_balance_rivet([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rivet([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rivet([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bolt([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -543,
        "threshold_run_signal_density_band_span_gap_delta_balance_bolt([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bolt([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bolt([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bolt([1, 8, 9, 3, 0, 1], 3, 6)": -430,
        "outlier_run_signal_density_band_span_gap_delta_balance_bolt([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bolt([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bolt([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_screw([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -550,
        "threshold_run_signal_density_band_span_gap_delta_balance_screw([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_screw([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_screw([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_screw([1, 8, 9, 3, 0, 1], 3, 6)": -437,
        "outlier_run_signal_density_band_span_gap_delta_balance_screw([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_screw([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_screw([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_nail([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -557,
        "threshold_run_signal_density_band_span_gap_delta_balance_nail([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_nail([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_nail([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_nail([1, 8, 9, 3, 0, 1], 3, 6)": -442,
        "outlier_run_signal_density_band_span_gap_delta_balance_nail([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_nail([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_nail([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_thread([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -567,
        "threshold_run_signal_density_band_span_gap_delta_balance_thread([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_thread([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_thread([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_thread([1, 8, 9, 3, 0, 1], 3, 6)": -449,
        "outlier_run_signal_density_band_span_gap_delta_balance_thread([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_thread([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_thread([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_weave([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -571,
        "threshold_run_signal_density_band_span_gap_delta_balance_weave([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_weave([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_weave([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_weave([1, 8, 9, 3, 0, 1], 3, 6)": -454,
        "outlier_run_signal_density_band_span_gap_delta_balance_weave([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_weave([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_weave([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stitch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -580,
        "threshold_run_signal_density_band_span_gap_delta_balance_stitch([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stitch([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stitch([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stitch([1, 8, 9, 3, 0, 1], 3, 6)": -461,
        "outlier_run_signal_density_band_span_gap_delta_balance_stitch([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stitch([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stitch([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lace([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -584,
        "threshold_run_signal_density_band_span_gap_delta_balance_lace([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lace([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lace([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lace([1, 8, 9, 3, 0, 1], 3, 6)": -465,
        "outlier_run_signal_density_band_span_gap_delta_balance_lace([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lace([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lace([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cord([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -593,
        "threshold_run_signal_density_band_span_gap_delta_balance_cord([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cord([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cord([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cord([1, 8, 9, 3, 0, 1], 3, 6)": -473,
        "outlier_run_signal_density_band_span_gap_delta_balance_cord([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cord([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cord([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fiber([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -600,
        "threshold_run_signal_density_band_span_gap_delta_balance_fiber([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fiber([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fiber([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fiber([1, 8, 9, 3, 0, 1], 3, 6)": -480,
        "outlier_run_signal_density_band_span_gap_delta_balance_fiber([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fiber([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fiber([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_strand([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -607,
        "threshold_run_signal_density_band_span_gap_delta_balance_strand([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_strand([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_strand([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_strand([1, 8, 9, 3, 0, 1], 3, 6)": -484,
        "outlier_run_signal_density_band_span_gap_delta_balance_strand([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_strand([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_strand([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_twine([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -620,
        "threshold_run_signal_density_band_span_gap_delta_balance_twine([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_twine([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_twine([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_twine([1, 8, 9, 3, 0, 1], 3, 6)": -493,
        "outlier_run_signal_density_band_span_gap_delta_balance_twine([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_twine([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_twine([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_yarn([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -632,
        "threshold_run_signal_density_band_span_gap_delta_balance_yarn([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_yarn([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_yarn([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_yarn([1, 8, 9, 3, 0, 1], 3, 6)": -503,
        "outlier_run_signal_density_band_span_gap_delta_balance_yarn([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_yarn([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_yarn([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_loom([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -642,
        "threshold_run_signal_density_band_span_gap_delta_balance_loom([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_loom([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_loom([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_loom([1, 8, 9, 3, 0, 1], 3, 6)": -512,
        "outlier_run_signal_density_band_span_gap_delta_balance_loom([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_loom([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_loom([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_braid([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -646,
        "threshold_run_signal_density_band_span_gap_delta_balance_braid([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_braid([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_braid([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_braid([1, 8, 9, 3, 0, 1], 3, 6)": -517,
        "outlier_run_signal_density_band_span_gap_delta_balance_braid([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_braid([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_braid([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mesh([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -656,
        "threshold_run_signal_density_band_span_gap_delta_balance_mesh([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mesh([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mesh([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mesh([1, 8, 9, 3, 0, 1], 3, 6)": -524,
        "outlier_run_signal_density_band_span_gap_delta_balance_mesh([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mesh([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mesh([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_net([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -663,
        "threshold_run_signal_density_band_span_gap_delta_balance_net([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_net([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_net([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_net([1, 8, 9, 3, 0, 1], 3, 6)": -528,
        "outlier_run_signal_density_band_span_gap_delta_balance_net([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_net([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_net([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_web([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -676,
        "threshold_run_signal_density_band_span_gap_delta_balance_web([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_web([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_web([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_web([1, 8, 9, 3, 0, 1], 3, 6)": -538,
        "outlier_run_signal_density_band_span_gap_delta_balance_web([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_web([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_web([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_grid([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -687,
        "threshold_run_signal_density_band_span_gap_delta_balance_grid([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_grid([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_grid([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_grid([1, 8, 9, 3, 0, 1], 3, 6)": -547,
        "outlier_run_signal_density_band_span_gap_delta_balance_grid([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_grid([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_grid([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cloth([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -700,
        "threshold_run_signal_density_band_span_gap_delta_balance_cloth([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cloth([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cloth([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cloth([1, 8, 9, 3, 0, 1], 3, 6)": -557,
        "outlier_run_signal_density_band_span_gap_delta_balance_cloth([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cloth([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cloth([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_knit([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -711,
        "threshold_run_signal_density_band_span_gap_delta_balance_knit([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_knit([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_knit([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_knit([1, 8, 9, 3, 0, 1], 3, 6)": -566,
        "outlier_run_signal_density_band_span_gap_delta_balance_knit([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_knit([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_knit([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_loop([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -715,
        "threshold_run_signal_density_band_span_gap_delta_balance_loop([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_loop([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_loop([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_loop([1, 8, 9, 3, 0, 1], 3, 6)": -571,
        "outlier_run_signal_density_band_span_gap_delta_balance_loop([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_loop([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_loop([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tile([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -724,
        "threshold_run_signal_density_band_span_gap_delta_balance_tile([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tile([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tile([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tile([1, 8, 9, 3, 0, 1], 3, 6)": -578,
        "outlier_run_signal_density_band_span_gap_delta_balance_tile([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tile([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tile([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_patch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -734,
        "threshold_run_signal_density_band_span_gap_delta_balance_patch([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_patch([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_patch([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_patch([1, 8, 9, 3, 0, 1], 3, 6)": -585,
        "outlier_run_signal_density_band_span_gap_delta_balance_patch([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_patch([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_patch([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_seam([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -740,
        "threshold_run_signal_density_band_span_gap_delta_balance_seam([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_seam([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_seam([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_seam([1, 8, 9, 3, 0, 1], 3, 6)": -590,
        "outlier_run_signal_density_band_span_gap_delta_balance_seam([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_seam([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_seam([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_node([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -744,
        "threshold_run_signal_density_band_span_gap_delta_balance_node([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_node([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_node([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_node([1, 8, 9, 3, 0, 1], 3, 6)": -594,
        "outlier_run_signal_density_band_span_gap_delta_balance_node([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_node([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_node([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ring([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -754,
        "threshold_run_signal_density_band_span_gap_delta_balance_ring([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ring([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ring([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ring([1, 8, 9, 3, 0, 1], 3, 6)": -601,
        "outlier_run_signal_density_band_span_gap_delta_balance_ring([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ring([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ring([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bead([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -761,
        "threshold_run_signal_density_band_span_gap_delta_balance_bead([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bead([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bead([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bead([1, 8, 9, 3, 0, 1], 3, 6)": -606,
        "outlier_run_signal_density_band_span_gap_delta_balance_bead([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bead([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bead([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_charm([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -770,
        "threshold_run_signal_density_band_span_gap_delta_balance_charm([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_charm([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_charm([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_charm([1, 8, 9, 3, 0, 1], 3, 6)": -613,
        "outlier_run_signal_density_band_span_gap_delta_balance_charm([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_charm([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_charm([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gem([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -780,
        "threshold_run_signal_density_band_span_gap_delta_balance_gem([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gem([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gem([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gem([1, 8, 9, 3, 0, 1], 3, 6)": -620,
        "outlier_run_signal_density_band_span_gap_delta_balance_gem([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gem([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gem([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jewel([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -786,
        "threshold_run_signal_density_band_span_gap_delta_balance_jewel([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jewel([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jewel([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jewel([1, 8, 9, 3, 0, 1], 3, 6)": -625,
        "outlier_run_signal_density_band_span_gap_delta_balance_jewel([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jewel([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jewel([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_facet([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -791,
        "threshold_run_signal_density_band_span_gap_delta_balance_facet([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_facet([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_facet([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_facet([1, 8, 9, 3, 0, 1], 3, 6)": -629,
        "outlier_run_signal_density_band_span_gap_delta_balance_facet([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_facet([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_facet([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_prism([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -800,
        "threshold_run_signal_density_band_span_gap_delta_balance_prism([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_prism([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_prism([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_prism([1, 8, 9, 3, 0, 1], 3, 6)": -637,
        "outlier_run_signal_density_band_span_gap_delta_balance_prism([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_prism([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_prism([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_opal([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -807,
        "threshold_run_signal_density_band_span_gap_delta_balance_opal([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_opal([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_opal([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_opal([1, 8, 9, 3, 0, 1], 3, 6)": -644,
        "outlier_run_signal_density_band_span_gap_delta_balance_opal([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_opal([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_opal([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ruby([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -814,
        "threshold_run_signal_density_band_span_gap_delta_balance_ruby([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ruby([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ruby([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ruby([1, 8, 9, 3, 0, 1], 3, 6)": -648,
        "outlier_run_signal_density_band_span_gap_delta_balance_ruby([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ruby([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ruby([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pearl([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -824,
        "threshold_run_signal_density_band_span_gap_delta_balance_pearl([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pearl([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pearl([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pearl([1, 8, 9, 3, 0, 1], 3, 6)": -658,
        "outlier_run_signal_density_band_span_gap_delta_balance_pearl([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pearl([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pearl([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_agate([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -834,
        "threshold_run_signal_density_band_span_gap_delta_balance_agate([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_agate([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_agate([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_agate([1, 8, 9, 3, 0, 1], 3, 6)": -665,
        "outlier_run_signal_density_band_span_gap_delta_balance_agate([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_agate([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_agate([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_topaz([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -841,
        "threshold_run_signal_density_band_span_gap_delta_balance_topaz([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_topaz([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_topaz([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_topaz([1, 8, 9, 3, 0, 1], 3, 6)": -670,
        "outlier_run_signal_density_band_span_gap_delta_balance_topaz([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_topaz([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_topaz([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_amber([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -848,
        "threshold_run_signal_density_band_span_gap_delta_balance_amber([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_amber([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_amber([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_amber([1, 8, 9, 3, 0, 1], 3, 6)": -677,
        "outlier_run_signal_density_band_span_gap_delta_balance_amber([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_amber([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_amber([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_garnet([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -854,
        "threshold_run_signal_density_band_span_gap_delta_balance_garnet([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_garnet([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_garnet([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_garnet([1, 8, 9, 3, 0, 1], 3, 6)": -682,
        "outlier_run_signal_density_band_span_gap_delta_balance_garnet([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_garnet([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_garnet([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_onyx([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -864,
        "threshold_run_signal_density_band_span_gap_delta_balance_onyx([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_onyx([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_onyx([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_onyx([1, 8, 9, 3, 0, 1], 3, 6)": -689,
        "outlier_run_signal_density_band_span_gap_delta_balance_onyx([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_onyx([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_onyx([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_quartz([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -868,
        "threshold_run_signal_density_band_span_gap_delta_balance_quartz([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_quartz([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_quartz([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_quartz([1, 8, 9, 3, 0, 1], 3, 6)": -694,
        "outlier_run_signal_density_band_span_gap_delta_balance_quartz([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_quartz([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_quartz([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jade([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -877,
        "threshold_run_signal_density_band_span_gap_delta_balance_jade([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jade([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jade([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jade([1, 8, 9, 3, 0, 1], 3, 6)": -701,
        "outlier_run_signal_density_band_span_gap_delta_balance_jade([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jade([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jade([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_beryl([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -887,
        "threshold_run_signal_density_band_span_gap_delta_balance_beryl([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_beryl([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_beryl([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_beryl([1, 8, 9, 3, 0, 1], 3, 6)": -708,
        "outlier_run_signal_density_band_span_gap_delta_balance_beryl([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_beryl([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_beryl([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_coral([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -894,
        "threshold_run_signal_density_band_span_gap_delta_balance_coral([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_coral([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_coral([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_coral([1, 8, 9, 3, 0, 1], 3, 6)": -713,
        "outlier_run_signal_density_band_span_gap_delta_balance_coral([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_coral([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_coral([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lapis([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -899,
        "threshold_run_signal_density_band_span_gap_delta_balance_lapis([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lapis([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lapis([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lapis([1, 8, 9, 3, 0, 1], 3, 6)": -717,
        "outlier_run_signal_density_band_span_gap_delta_balance_lapis([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lapis([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lapis([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_zircon([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -909,
        "threshold_run_signal_density_band_span_gap_delta_balance_zircon([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_zircon([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_zircon([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_zircon([1, 8, 9, 3, 0, 1], 3, 6)": -724,
        "outlier_run_signal_density_band_span_gap_delta_balance_zircon([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_zircon([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_zircon([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spinel([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -915,
        "threshold_run_signal_density_band_span_gap_delta_balance_spinel([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spinel([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spinel([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spinel([1, 8, 9, 3, 0, 1], 3, 6)": -729,
        "outlier_run_signal_density_band_span_gap_delta_balance_spinel([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spinel([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spinel([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jasper([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -922,
        "threshold_run_signal_density_band_span_gap_delta_balance_jasper([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jasper([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_jasper([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jasper([1, 8, 9, 3, 0, 1], 3, 6)": -736,
        "outlier_run_signal_density_band_span_gap_delta_balance_jasper([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jasper([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_jasper([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_marble([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -932,
        "threshold_run_signal_density_band_span_gap_delta_balance_marble([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_marble([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_marble([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_marble([1, 8, 9, 3, 0, 1], 3, 6)": -743,
        "outlier_run_signal_density_band_span_gap_delta_balance_marble([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_marble([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_marble([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_basalt([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -941,
        "threshold_run_signal_density_band_span_gap_delta_balance_basalt([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_basalt([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_basalt([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_basalt([1, 8, 9, 3, 0, 1], 3, 6)": -751,
        "outlier_run_signal_density_band_span_gap_delta_balance_basalt([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_basalt([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_basalt([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_slate([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -948,
        "threshold_run_signal_density_band_span_gap_delta_balance_slate([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_slate([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_slate([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_slate([1, 8, 9, 3, 0, 1], 3, 6)": -758,
        "outlier_run_signal_density_band_span_gap_delta_balance_slate([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_slate([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_slate([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shale([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -958,
        "threshold_run_signal_density_band_span_gap_delta_balance_shale([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shale([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shale([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shale([1, 8, 9, 3, 0, 1], 3, 6)": -765,
        "outlier_run_signal_density_band_span_gap_delta_balance_shale([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shale([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shale([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shard([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -964,
        "threshold_run_signal_density_band_span_gap_delta_balance_shard([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shard([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shard([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shard([1, 8, 9, 3, 0, 1], 3, 6)": -770,
        "outlier_run_signal_density_band_span_gap_delta_balance_shard([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shard([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shard([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gravel([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -974,
        "threshold_run_signal_density_band_span_gap_delta_balance_gravel([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gravel([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gravel([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gravel([1, 8, 9, 3, 0, 1], 3, 6)": -777,
        "outlier_run_signal_density_band_span_gap_delta_balance_gravel([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gravel([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gravel([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pebble([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -981,
        "threshold_run_signal_density_band_span_gap_delta_balance_pebble([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pebble([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pebble([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pebble([1, 8, 9, 3, 0, 1], 3, 6)": -782,
        "outlier_run_signal_density_band_span_gap_delta_balance_pebble([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pebble([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pebble([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cobble([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -990,
        "threshold_run_signal_density_band_span_gap_delta_balance_cobble([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cobble([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cobble([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cobble([1, 8, 9, 3, 0, 1], 3, 6)": -789,
        "outlier_run_signal_density_band_span_gap_delta_balance_cobble([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cobble([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cobble([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rubble([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1000,
        "threshold_run_signal_density_band_span_gap_delta_balance_rubble([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rubble([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rubble([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rubble([1, 8, 9, 3, 0, 1], 3, 6)": -796,
        "outlier_run_signal_density_band_span_gap_delta_balance_rubble([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rubble([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rubble([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_talus([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1007,
        "threshold_run_signal_density_band_span_gap_delta_balance_talus([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_talus([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_talus([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_talus([1, 8, 9, 3, 0, 1], 3, 6)": -801,
        "outlier_run_signal_density_band_span_gap_delta_balance_talus([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_talus([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_talus([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_scree([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1012,
        "threshold_run_signal_density_band_span_gap_delta_balance_scree([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_scree([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_scree([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_scree([1, 8, 9, 3, 0, 1], 3, 6)": -805,
        "outlier_run_signal_density_band_span_gap_delta_balance_scree([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_scree([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_scree([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cairn([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1019,
        "threshold_run_signal_density_band_span_gap_delta_balance_cairn([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cairn([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cairn([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cairn([1, 8, 9, 3, 0, 1], 3, 6)": -812,
        "outlier_run_signal_density_band_span_gap_delta_balance_cairn([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cairn([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cairn([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mound([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1029,
        "threshold_run_signal_density_band_span_gap_delta_balance_mound([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mound([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mound([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mound([1, 8, 9, 3, 0, 1], 3, 6)": -819,
        "outlier_run_signal_density_band_span_gap_delta_balance_mound([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mound([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mound([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_dune([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1035,
        "threshold_run_signal_density_band_span_gap_delta_balance_dune([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_dune([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_dune([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_dune([1, 8, 9, 3, 0, 1], 3, 6)": -824,
        "outlier_run_signal_density_band_span_gap_delta_balance_dune([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_dune([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_dune([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ridge([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1045,
        "threshold_run_signal_density_band_span_gap_delta_balance_ridge([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ridge([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ridge([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ridge([1, 8, 9, 3, 0, 1], 3, 6)": -831,
        "outlier_run_signal_density_band_span_gap_delta_balance_ridge([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ridge([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ridge([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ledge([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1049,
        "threshold_run_signal_density_band_span_gap_delta_balance_ledge([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ledge([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_ledge([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ledge([1, 8, 9, 3, 0, 1], 3, 6)": -836,
        "outlier_run_signal_density_band_span_gap_delta_balance_ledge([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ledge([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_ledge([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_butte([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1059,
        "threshold_run_signal_density_band_span_gap_delta_balance_butte([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_butte([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_butte([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_butte([1, 8, 9, 3, 0, 1], 3, 6)": -843,
        "outlier_run_signal_density_band_span_gap_delta_balance_butte([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_butte([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_butte([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mesa([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1068,
        "threshold_run_signal_density_band_span_gap_delta_balance_mesa([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mesa([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mesa([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mesa([1, 8, 9, 3, 0, 1], 3, 6)": -851,
        "outlier_run_signal_density_band_span_gap_delta_balance_mesa([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mesa([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mesa([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cliff([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1075,
        "threshold_run_signal_density_band_span_gap_delta_balance_cliff([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cliff([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cliff([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cliff([1, 8, 9, 3, 0, 1], 3, 6)": -858,
        "outlier_run_signal_density_band_span_gap_delta_balance_cliff([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cliff([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cliff([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_crag([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1085,
        "threshold_run_signal_density_band_span_gap_delta_balance_crag([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_crag([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_crag([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_crag([1, 8, 9, 3, 0, 1], 3, 6)": -865,
        "outlier_run_signal_density_band_span_gap_delta_balance_crag([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_crag([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_crag([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_canyon([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1092,
        "threshold_run_signal_density_band_span_gap_delta_balance_canyon([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_canyon([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_canyon([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_canyon([1, 8, 9, 3, 0, 1], 3, 6)": -870,
        "outlier_run_signal_density_band_span_gap_delta_balance_canyon([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_canyon([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_canyon([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gully([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1101,
        "threshold_run_signal_density_band_span_gap_delta_balance_gully([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gully([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gully([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gully([1, 8, 9, 3, 0, 1], 3, 6)": -877,
        "outlier_run_signal_density_band_span_gap_delta_balance_gully([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gully([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gully([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_basin([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1111,
        "threshold_run_signal_density_band_span_gap_delta_balance_basin([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_basin([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_basin([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_basin([1, 8, 9, 3, 0, 1], 3, 6)": -884,
        "outlier_run_signal_density_band_span_gap_delta_balance_basin([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_basin([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_basin([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_grove([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1115,
        "threshold_run_signal_density_band_span_gap_delta_balance_grove([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_grove([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_grove([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_grove([1, 8, 9, 3, 0, 1], 3, 6)": -889,
        "outlier_run_signal_density_band_span_gap_delta_balance_grove([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_grove([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_grove([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_forest([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1125,
        "threshold_run_signal_density_band_span_gap_delta_balance_forest([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_forest([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_forest([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_forest([1, 8, 9, 3, 0, 1], 3, 6)": -896,
        "outlier_run_signal_density_band_span_gap_delta_balance_forest([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_forest([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_forest([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_canopy([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1132,
        "threshold_run_signal_density_band_span_gap_delta_balance_canopy([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_canopy([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_canopy([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_canopy([1, 8, 9, 3, 0, 1], 3, 6)": -901,
        "outlier_run_signal_density_band_span_gap_delta_balance_canopy([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_canopy([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_canopy([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_branch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1141,
        "threshold_run_signal_density_band_span_gap_delta_balance_branch([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_branch([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_branch([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_branch([1, 8, 9, 3, 0, 1], 3, 6)": -908,
        "outlier_run_signal_density_band_span_gap_delta_balance_branch([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_branch([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_branch([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_leaf([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1151,
        "threshold_run_signal_density_band_span_gap_delta_balance_leaf([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_leaf([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_leaf([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_leaf([1, 8, 9, 3, 0, 1], 3, 6)": -915,
        "outlier_run_signal_density_band_span_gap_delta_balance_leaf([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_leaf([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_leaf([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bough([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1155,
        "threshold_run_signal_density_band_span_gap_delta_balance_bough([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bough([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bough([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bough([1, 8, 9, 3, 0, 1], 3, 6)": -920,
        "outlier_run_signal_density_band_span_gap_delta_balance_bough([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bough([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bough([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_twig([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1165,
        "threshold_run_signal_density_band_span_gap_delta_balance_twig([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_twig([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_twig([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_twig([1, 8, 9, 3, 0, 1], 3, 6)": -927,
        "outlier_run_signal_density_band_span_gap_delta_balance_twig([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_twig([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_twig([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sprout([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1174,
        "threshold_run_signal_density_band_span_gap_delta_balance_sprout([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sprout([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sprout([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sprout([1, 8, 9, 3, 0, 1], 3, 6)": -935,
        "outlier_run_signal_density_band_span_gap_delta_balance_sprout([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sprout([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sprout([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bud([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1178,
        "threshold_run_signal_density_band_span_gap_delta_balance_bud([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bud([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bud([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bud([1, 8, 9, 3, 0, 1], 3, 6)": -939,
        "outlier_run_signal_density_band_span_gap_delta_balance_bud([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bud([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bud([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flower([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1188,
        "threshold_run_signal_density_band_span_gap_delta_balance_flower([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flower([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_flower([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flower([1, 8, 9, 3, 0, 1], 3, 6)": -946,
        "outlier_run_signal_density_band_span_gap_delta_balance_flower([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flower([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_flower([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_petal([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1195,
        "threshold_run_signal_density_band_span_gap_delta_balance_petal([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_petal([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_petal([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_petal([1, 8, 9, 3, 0, 1], 3, 6)": -951,
        "outlier_run_signal_density_band_span_gap_delta_balance_petal([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_petal([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_petal([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_seed([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1202,
        "threshold_run_signal_density_band_span_gap_delta_balance_seed([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_seed([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_seed([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_seed([1, 8, 9, 3, 0, 1], 3, 6)": -958,
        "outlier_run_signal_density_band_span_gap_delta_balance_seed([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_seed([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_seed([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fruit([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1212,
        "threshold_run_signal_density_band_span_gap_delta_balance_fruit([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fruit([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fruit([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fruit([1, 8, 9, 3, 0, 1], 3, 6)": -965,
        "outlier_run_signal_density_band_span_gap_delta_balance_fruit([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fruit([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fruit([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tree([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1221,
        "threshold_run_signal_density_band_span_gap_delta_balance_tree([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tree([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tree([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tree([1, 8, 9, 3, 0, 1], 3, 6)": -973,
        "outlier_run_signal_density_band_span_gap_delta_balance_tree([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tree([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tree([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_trunk([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1231,
        "threshold_run_signal_density_band_span_gap_delta_balance_trunk([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_trunk([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_trunk([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_trunk([1, 8, 9, 3, 0, 1], 3, 6)": -980,
        "outlier_run_signal_density_band_span_gap_delta_balance_trunk([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_trunk([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_trunk([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bark([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1240,
        "threshold_run_signal_density_band_span_gap_delta_balance_bark([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bark([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bark([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bark([1, 8, 9, 3, 0, 1], 3, 6)": -987,
        "outlier_run_signal_density_band_span_gap_delta_balance_bark([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bark([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bark([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_limb([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1250,
        "threshold_run_signal_density_band_span_gap_delta_balance_limb([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_limb([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_limb([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_limb([1, 8, 9, 3, 0, 1], 3, 6)": -994,
        "outlier_run_signal_density_band_span_gap_delta_balance_limb([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_limb([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_limb([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stump([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1259,
        "threshold_run_signal_density_band_span_gap_delta_balance_stump([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stump([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stump([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stump([1, 8, 9, 3, 0, 1], 3, 6)": -1002,
        "outlier_run_signal_density_band_span_gap_delta_balance_stump([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stump([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stump([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1266,
        "threshold_run_signal_density_band_span_gap_delta_balance_sap([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sap([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sap([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sap([1, 8, 9, 3, 0, 1], 3, 6)": -1009,
        "outlier_run_signal_density_band_span_gap_delta_balance_sap([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sap([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sap([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shoot([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1276,
        "threshold_run_signal_density_band_span_gap_delta_balance_shoot([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shoot([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_shoot([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shoot([1, 8, 9, 3, 0, 1], 3, 6)": -1016,
        "outlier_run_signal_density_band_span_gap_delta_balance_shoot([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shoot([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_shoot([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stem([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1282,
        "threshold_run_signal_density_band_span_gap_delta_balance_stem([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stem([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stem([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stem([1, 8, 9, 3, 0, 1], 3, 6)": -1021,
        "outlier_run_signal_density_band_span_gap_delta_balance_stem([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stem([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stem([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sprig([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1292,
        "threshold_run_signal_density_band_span_gap_delta_balance_sprig([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sprig([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sprig([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sprig([1, 8, 9, 3, 0, 1], 3, 6)": -1028,
        "outlier_run_signal_density_band_span_gap_delta_balance_sprig([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sprig([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sprig([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_frond([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1299,
        "threshold_run_signal_density_band_span_gap_delta_balance_frond([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_frond([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_frond([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_frond([1, 8, 9, 3, 0, 1], 3, 6)": -1033,
        "outlier_run_signal_density_band_span_gap_delta_balance_frond([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_frond([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_frond([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fern([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1308,
        "threshold_run_signal_density_band_span_gap_delta_balance_fern([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fern([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fern([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fern([1, 8, 9, 3, 0, 1], 3, 6)": -1040,
        "outlier_run_signal_density_band_span_gap_delta_balance_fern([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fern([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fern([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_moss([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1318,
        "threshold_run_signal_density_band_span_gap_delta_balance_moss([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_moss([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_moss([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_moss([1, 8, 9, 3, 0, 1], 3, 6)": -1047,
        "outlier_run_signal_density_band_span_gap_delta_balance_moss([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_moss([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_moss([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lichen([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1327,
        "threshold_run_signal_density_band_span_gap_delta_balance_lichen([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lichen([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lichen([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lichen([1, 8, 9, 3, 0, 1], 3, 6)": -1055,
        "outlier_run_signal_density_band_span_gap_delta_balance_lichen([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lichen([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lichen([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_algae([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1334,
        "threshold_run_signal_density_band_span_gap_delta_balance_algae([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_algae([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_algae([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_algae([1, 8, 9, 3, 0, 1], 3, 6)": -1062,
        "outlier_run_signal_density_band_span_gap_delta_balance_algae([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_algae([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_algae([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_kelp([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1344,
        "threshold_run_signal_density_band_span_gap_delta_balance_kelp([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_kelp([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_kelp([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_kelp([1, 8, 9, 3, 0, 1], 3, 6)": -1069,
        "outlier_run_signal_density_band_span_gap_delta_balance_kelp([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_kelp([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_kelp([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_reed([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1353,
        "threshold_run_signal_density_band_span_gap_delta_balance_reed([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_reed([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_reed([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_reed([1, 8, 9, 3, 0, 1], 3, 6)": -1077,
        "outlier_run_signal_density_band_span_gap_delta_balance_reed([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_reed([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_reed([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rush([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1358,
        "threshold_run_signal_density_band_span_gap_delta_balance_rush([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rush([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rush([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rush([1, 8, 9, 3, 0, 1], 3, 6)": -1081,
        "outlier_run_signal_density_band_span_gap_delta_balance_rush([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rush([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rush([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_brook([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1368,
        "threshold_run_signal_density_band_span_gap_delta_balance_brook([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_brook([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_brook([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_brook([1, 8, 9, 3, 0, 1], 3, 6)": -1088,
        "outlier_run_signal_density_band_span_gap_delta_balance_brook([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_brook([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_brook([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stream([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1377,
        "threshold_run_signal_density_band_span_gap_delta_balance_stream([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stream([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stream([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stream([1, 8, 9, 3, 0, 1], 3, 6)": -1096,
        "outlier_run_signal_density_band_span_gap_delta_balance_stream([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stream([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stream([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_creek([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1384,
        "threshold_run_signal_density_band_span_gap_delta_balance_creek([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_creek([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_creek([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_creek([1, 8, 9, 3, 0, 1], 3, 6)": -1103,
        "outlier_run_signal_density_band_span_gap_delta_balance_creek([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_creek([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_creek([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_river([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1394,
        "threshold_run_signal_density_band_span_gap_delta_balance_river([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_river([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_river([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_river([1, 8, 9, 3, 0, 1], 3, 6)": -1110,
        "outlier_run_signal_density_band_span_gap_delta_balance_river([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_river([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_river([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pond([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1403,
        "threshold_run_signal_density_band_span_gap_delta_balance_pond([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pond([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pond([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pond([1, 8, 9, 3, 0, 1], 3, 6)": -1117,
        "outlier_run_signal_density_band_span_gap_delta_balance_pond([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pond([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pond([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lake([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1410,
        "threshold_run_signal_density_band_span_gap_delta_balance_lake([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lake([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lake([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lake([1, 8, 9, 3, 0, 1], 3, 6)": -1122,
        "outlier_run_signal_density_band_span_gap_delta_balance_lake([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lake([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lake([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lagoon([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1417,
        "threshold_run_signal_density_band_span_gap_delta_balance_lagoon([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lagoon([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lagoon([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lagoon([1, 8, 9, 3, 0, 1], 3, 6)": -1129,
        "outlier_run_signal_density_band_span_gap_delta_balance_lagoon([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lagoon([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lagoon([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_marsh([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1427,
        "threshold_run_signal_density_band_span_gap_delta_balance_marsh([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_marsh([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_marsh([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_marsh([1, 8, 9, 3, 0, 1], 3, 6)": -1136,
        "outlier_run_signal_density_band_span_gap_delta_balance_marsh([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_marsh([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_marsh([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_swamp([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1436,
        "threshold_run_signal_density_band_span_gap_delta_balance_swamp([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_swamp([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_swamp([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_swamp([1, 8, 9, 3, 0, 1], 3, 6)": -1144,
        "outlier_run_signal_density_band_span_gap_delta_balance_swamp([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_swamp([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_swamp([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bog([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1443,
        "threshold_run_signal_density_band_span_gap_delta_balance_bog([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bog([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bog([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bog([1, 8, 9, 3, 0, 1], 3, 6)": -1151,
        "outlier_run_signal_density_band_span_gap_delta_balance_bog([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bog([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bog([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fen([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1453,
        "threshold_run_signal_density_band_span_gap_delta_balance_fen([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fen([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_fen([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fen([1, 8, 9, 3, 0, 1], 3, 6)": -1158,
        "outlier_run_signal_density_band_span_gap_delta_balance_fen([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fen([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_fen([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mere([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1462,
        "threshold_run_signal_density_band_span_gap_delta_balance_mere([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mere([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mere([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mere([1, 8, 9, 3, 0, 1], 3, 6)": -1166,
        "outlier_run_signal_density_band_span_gap_delta_balance_mere([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mere([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mere([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pool([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1471,
        "threshold_run_signal_density_band_span_gap_delta_balance_pool([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pool([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pool([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pool([1, 8, 9, 3, 0, 1], 3, 6)": -1173,
        "outlier_run_signal_density_band_span_gap_delta_balance_pool([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pool([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pool([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cove([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1481,
        "threshold_run_signal_density_band_span_gap_delta_balance_cove([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cove([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_cove([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cove([1, 8, 9, 3, 0, 1], 3, 6)": -1180,
        "outlier_run_signal_density_band_span_gap_delta_balance_cove([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cove([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_cove([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bay([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1490,
        "threshold_run_signal_density_band_span_gap_delta_balance_bay([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bay([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_bay([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bay([1, 8, 9, 3, 0, 1], 3, 6)": -1188,
        "outlier_run_signal_density_band_span_gap_delta_balance_bay([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bay([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_bay([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_harbor([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1497,
        "threshold_run_signal_density_band_span_gap_delta_balance_harbor([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_harbor([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_harbor([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_harbor([1, 8, 9, 3, 0, 1], 3, 6)": -1195,
        "outlier_run_signal_density_band_span_gap_delta_balance_harbor([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_harbor([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_harbor([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_inlet([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1506,
        "threshold_run_signal_density_band_span_gap_delta_balance_inlet([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_inlet([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_inlet([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_inlet([1, 8, 9, 3, 0, 1], 3, 6)": -1202,
        "outlier_run_signal_density_band_span_gap_delta_balance_inlet([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_inlet([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_inlet([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_port([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1516,
        "threshold_run_signal_density_band_span_gap_delta_balance_port([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_port([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_port([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_port([1, 8, 9, 3, 0, 1], 3, 6)": -1209,
        "outlier_run_signal_density_band_span_gap_delta_balance_port([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_port([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_port([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_dock([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1525,
        "threshold_run_signal_density_band_span_gap_delta_balance_dock([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_dock([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_dock([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_dock([1, 8, 9, 3, 0, 1], 3, 6)": -1217,
        "outlier_run_signal_density_band_span_gap_delta_balance_dock([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_dock([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_dock([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pier([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1532,
        "threshold_run_signal_density_band_span_gap_delta_balance_pier([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pier([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pier([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pier([1, 8, 9, 3, 0, 1], 3, 6)": -1224,
        "outlier_run_signal_density_band_span_gap_delta_balance_pier([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pier([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pier([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_quay([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1542,
        "threshold_run_signal_density_band_span_gap_delta_balance_quay([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_quay([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_quay([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_quay([1, 8, 9, 3, 0, 1], 3, 6)": -1231,
        "outlier_run_signal_density_band_span_gap_delta_balance_quay([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_quay([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_quay([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wharf([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1551,
        "threshold_run_signal_density_band_span_gap_delta_balance_wharf([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wharf([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wharf([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wharf([1, 8, 9, 3, 0, 1], 3, 6)": -1238,
        "outlier_run_signal_density_band_span_gap_delta_balance_wharf([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wharf([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wharf([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_berth([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1560,
        "threshold_run_signal_density_band_span_gap_delta_balance_berth([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_berth([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_berth([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_berth([1, 8, 9, 3, 0, 1], 3, 6)": -1246,
        "outlier_run_signal_density_band_span_gap_delta_balance_berth([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_berth([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_berth([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_buoy([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1567,
        "threshold_run_signal_density_band_span_gap_delta_balance_buoy([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_buoy([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_buoy([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_buoy([1, 8, 9, 3, 0, 1], 3, 6)": -1253,
        "outlier_run_signal_density_band_span_gap_delta_balance_buoy([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_buoy([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_buoy([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_float([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1577,
        "threshold_run_signal_density_band_span_gap_delta_balance_float([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_float([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_float([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_float([1, 8, 9, 3, 0, 1], 3, 6)": -1260,
        "outlier_run_signal_density_band_span_gap_delta_balance_float([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_float([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_float([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_raft([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1586,
        "threshold_run_signal_density_band_span_gap_delta_balance_raft([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_raft([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_raft([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_raft([1, 8, 9, 3, 0, 1], 3, 6)": -1267,
        "outlier_run_signal_density_band_span_gap_delta_balance_raft([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_raft([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_raft([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sail([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1593,
        "threshold_run_signal_density_band_span_gap_delta_balance_sail([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sail([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_sail([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sail([1, 8, 9, 3, 0, 1], 3, 6)": -1272,
        "outlier_run_signal_density_band_span_gap_delta_balance_sail([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sail([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_sail([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mast([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1600,
        "threshold_run_signal_density_band_span_gap_delta_balance_mast([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mast([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_mast([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mast([1, 8, 9, 3, 0, 1], 3, 6)": -1279,
        "outlier_run_signal_density_band_span_gap_delta_balance_mast([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mast([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_mast([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_helm([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1610,
        "threshold_run_signal_density_band_span_gap_delta_balance_helm([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_helm([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_helm([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_helm([1, 8, 9, 3, 0, 1], 3, 6)": -1286,
        "outlier_run_signal_density_band_span_gap_delta_balance_helm([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_helm([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_helm([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rudder([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1616,
        "threshold_run_signal_density_band_span_gap_delta_balance_rudder([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rudder([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rudder([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rudder([1, 8, 9, 3, 0, 1], 3, 6)": -1291,
        "outlier_run_signal_density_band_span_gap_delta_balance_rudder([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rudder([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rudder([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tiller([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1623,
        "threshold_run_signal_density_band_span_gap_delta_balance_tiller([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tiller([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tiller([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tiller([1, 8, 9, 3, 0, 1], 3, 6)": -1298,
        "outlier_run_signal_density_band_span_gap_delta_balance_tiller([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tiller([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tiller([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wheel([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1630,
        "threshold_run_signal_density_band_span_gap_delta_balance_wheel([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wheel([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_wheel([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wheel([1, 8, 9, 3, 0, 1], 3, 6)": -1303,
        "outlier_run_signal_density_band_span_gap_delta_balance_wheel([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wheel([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_wheel([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_axle([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1639,
        "threshold_run_signal_density_band_span_gap_delta_balance_axle([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_axle([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_axle([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_axle([1, 8, 9, 3, 0, 1], 3, 6)": -1310,
        "outlier_run_signal_density_band_span_gap_delta_balance_axle([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_axle([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_axle([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_hub([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1644,
        "threshold_run_signal_density_band_span_gap_delta_balance_hub([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_hub([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_hub([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_hub([1, 8, 9, 3, 0, 1], 3, 6)": -1314,
        "outlier_run_signal_density_band_span_gap_delta_balance_hub([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_hub([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_hub([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spoke([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1653,
        "threshold_run_signal_density_band_span_gap_delta_balance_spoke([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spoke([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_spoke([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spoke([1, 8, 9, 3, 0, 1], 3, 6)": -1322,
        "outlier_run_signal_density_band_span_gap_delta_balance_spoke([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spoke([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_spoke([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tire([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1663,
        "threshold_run_signal_density_band_span_gap_delta_balance_tire([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tire([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tire([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tire([1, 8, 9, 3, 0, 1], 3, 6)": -1329,
        "outlier_run_signal_density_band_span_gap_delta_balance_tire([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tire([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tire([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tread([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1667,
        "threshold_run_signal_density_band_span_gap_delta_balance_tread([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tread([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tread([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tread([1, 8, 9, 3, 0, 1], 3, 6)": -1334,
        "outlier_run_signal_density_band_span_gap_delta_balance_tread([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tread([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tread([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_track([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1676,
        "threshold_run_signal_density_band_span_gap_delta_balance_track([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_track([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_track([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_track([1, 8, 9, 3, 0, 1], 3, 6)": -1341,
        "outlier_run_signal_density_band_span_gap_delta_balance_track([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_track([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_track([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_road([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1686,
        "threshold_run_signal_density_band_span_gap_delta_balance_road([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_road([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_road([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_road([1, 8, 9, 3, 0, 1], 3, 6)": -1348,
        "outlier_run_signal_density_band_span_gap_delta_balance_road([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_road([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_road([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lane([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1693,
        "threshold_run_signal_density_band_span_gap_delta_balance_lane([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lane([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_lane([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lane([1, 8, 9, 3, 0, 1], 3, 6)": -1353,
        "outlier_run_signal_density_band_span_gap_delta_balance_lane([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lane([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_lane([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_route([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1700,
        "threshold_run_signal_density_band_span_gap_delta_balance_route([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_route([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_route([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_route([1, 8, 9, 3, 0, 1], 3, 6)": -1360,
        "outlier_run_signal_density_band_span_gap_delta_balance_route([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_route([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_route([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_path([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1709,
        "threshold_run_signal_density_band_span_gap_delta_balance_path([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_path([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_path([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_path([1, 8, 9, 3, 0, 1], 3, 6)": -1367,
        "outlier_run_signal_density_band_span_gap_delta_balance_path([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_path([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_path([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_trail([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1719,
        "threshold_run_signal_density_band_span_gap_delta_balance_trail([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_trail([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_trail([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_trail([1, 8, 9, 3, 0, 1], 3, 6)": -1374,
        "outlier_run_signal_density_band_span_gap_delta_balance_trail([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_trail([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_trail([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_walk([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1723,
        "threshold_run_signal_density_band_span_gap_delta_balance_walk([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_walk([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_walk([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_walk([1, 8, 9, 3, 0, 1], 3, 6)": -1379,
        "outlier_run_signal_density_band_span_gap_delta_balance_walk([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_walk([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_walk([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_step([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1732,
        "threshold_run_signal_density_band_span_gap_delta_balance_step([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_step([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_step([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_step([1, 8, 9, 3, 0, 1], 3, 6)": -1387,
        "outlier_run_signal_density_band_span_gap_delta_balance_step([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_step([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_step([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stride([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1739,
        "threshold_run_signal_density_band_span_gap_delta_balance_stride([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stride([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_stride([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stride([1, 8, 9, 3, 0, 1], 3, 6)": -1394,
        "outlier_run_signal_density_band_span_gap_delta_balance_stride([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stride([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_stride([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pace([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1749,
        "threshold_run_signal_density_band_span_gap_delta_balance_pace([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pace([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pace([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pace([1, 8, 9, 3, 0, 1], 3, 6)": -1401,
        "outlier_run_signal_density_band_span_gap_delta_balance_pace([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pace([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pace([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gait([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1755,
        "threshold_run_signal_density_band_span_gap_delta_balance_gait([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gait([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_gait([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gait([1, 8, 9, 3, 0, 1], 3, 6)": -1406,
        "outlier_run_signal_density_band_span_gap_delta_balance_gait([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gait([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_gait([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tempo([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1762,
        "threshold_run_signal_density_band_span_gap_delta_balance_rhythm([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1767,
        "threshold_run_signal_density_band_span_gap_delta_balance_rhythm([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rhythm([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_rhythm([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pulse([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1776,
        "threshold_run_signal_density_band_span_gap_delta_balance_pulse([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pulse([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_pulse([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_beat([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1786,
        "threshold_run_signal_density_band_span_gap_delta_balance_beat([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_beat([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_beat([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_meter([3, 4, 7, 3, 5, 6, 9, 4], 3, 6)": -1795,
        "threshold_run_signal_density_band_span_gap_delta_balance_meter([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_meter([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_meter([], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tempo([7, 8], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tempo([3], 3, 6)": 0,
        "threshold_run_signal_density_band_span_gap_delta_balance_tempo([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tempo([1, 8, 9, 3, 0, 1], 3, 6)": -1413,
        "outlier_run_signal_density_band_span_gap_delta_balance_rhythm([1, 8, 9, 3, 0, 1], 3, 6)": -1417,
        "outlier_run_signal_density_band_span_gap_delta_balance_rhythm([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rhythm([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_rhythm([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pulse([1, 8, 9, 3, 0, 1], 3, 6)": -1425,
        "outlier_run_signal_density_band_span_gap_delta_balance_pulse([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pulse([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_pulse([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_beat([1, 8, 9, 3, 0, 1], 3, 6)": -1432,
        "outlier_run_signal_density_band_span_gap_delta_balance_beat([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_beat([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_beat([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_meter([1, 8, 9, 3, 0, 1], 3, 6)": -1439,
        "outlier_run_signal_density_band_span_gap_delta_balance_meter([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_meter([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_meter([], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tempo([3, 4, 5], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tempo([7], 3, 6)": 0,
        "outlier_run_signal_density_band_span_gap_delta_balance_tempo([], 3, 6)": 0,
        "sum(threshold_run_lengths(clamp([9, 1, 5, 3], 2, 6), 2, 6)) + sum(outlier_run_lengths(clamp([9, 1, 5, 3], 2, 6), 3, 5))": 6,
        "threshold_run_length_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_length_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 20,
        "threshold_longest_run(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_shortest_run(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 6,
        "threshold_run_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6) + outlier_run_delta([1, 3, 8, 9, 10, 5, 0], 3, 6)": 4,
        "threshold_run_ratio_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_ratio_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 4,
        "threshold_transition_count(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_transition_count(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 1,
        "threshold_transition_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_transition_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 2,
        "threshold_transition_density(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_transition_density(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 1,
        "threshold_transition_balance(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_transition_balance(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -3,
        "threshold_run_contrast(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_contrast(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 7,
        "threshold_run_contrast_delta(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_contrast_delta(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 7,
        "threshold_run_signal_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 11,
        "threshold_run_signal_density(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 3,
        "threshold_run_signal_density_delta(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_delta(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 3,
        "threshold_run_signal_density_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 1,
        "threshold_run_signal_density_gap(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_gap(clamp([9, 1, 5, 3], 2, 6), 3, 5)": 4,
        "threshold_run_signal_density_band(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -8,
        "threshold_run_signal_density_band_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -10,
        "threshold_run_signal_density_band_gap(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_gap(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -7,
        "threshold_run_signal_density_band_gap_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_gap_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -9,
        "threshold_run_signal_density_band_span(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -21,
        "threshold_run_signal_density_band_span_gap(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -20,
        "threshold_run_signal_density_band_span_gap_delta_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -24,
        "threshold_run_signal_density_band_span_gap_delta_balance(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -21,
        "threshold_run_signal_density_band_span_gap_delta_balance_mark(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mark(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -155,
        "threshold_run_signal_density_band_span_gap_delta_balance_stamp(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_stamp(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -162,
        "threshold_run_signal_density_band_span_gap_delta_balance_press(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_press(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -169,
        "threshold_run_signal_density_band_span_gap_delta_balance_pin(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pin(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -177,
        "threshold_run_signal_density_band_span_gap_delta_balance_snap(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_snap(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -180,
        "threshold_run_signal_density_band_span_gap_delta_balance_clasp(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_clasp(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -198,
        "threshold_run_signal_density_band_span_gap_delta_balance_latch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_latch(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -201,
        "threshold_run_signal_density_band_span_gap_delta_balance_hook(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_hook(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -208,
        "threshold_run_signal_density_band_span_gap_delta_balance_link(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_link(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -215,
        "threshold_run_signal_density_band_span_gap_delta_balance_chain(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_chain(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -222,
        "threshold_run_signal_density_band_span_gap_delta_balance_rope(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_rope(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -235,
        "threshold_run_signal_density_band_span_gap_delta_balance_knot(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_knot(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -241,
        "threshold_run_signal_density_band_span_gap_delta_balance_tie(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_tie(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -244,
        "threshold_run_signal_density_band_span_gap_delta_balance_bow(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bow(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -252,
        "threshold_run_signal_density_band_span_gap_delta_balance_arc(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_arc(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -259,
        "threshold_run_signal_density_band_span_gap_delta_balance_arch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_arch(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -272,
        "threshold_run_signal_density_band_span_gap_delta_balance_gate(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_gate(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -281,
        "threshold_run_signal_density_band_span_gap_delta_balance_guard(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_guard(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -288,
        "threshold_run_signal_density_band_span_gap_delta_balance_shield(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_shield(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -294,
        "threshold_run_signal_density_band_span_gap_delta_balance_wall(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_wall(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -295,
        "threshold_run_signal_density_band_span_gap_delta_balance_fort(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_fort(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -302,
        "threshold_run_signal_density_band_span_gap_delta_balance_keep(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_keep(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -306,
        "threshold_run_signal_density_band_span_gap_delta_balance_core(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_core(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -317,
        "threshold_run_signal_density_band_span_gap_delta_balance_root(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_root(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -331,
        "threshold_run_signal_density_band_span_gap_delta_balance_crown(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_crown(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -338,
        "threshold_run_signal_density_band_span_gap_delta_balance_halo(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_halo(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -343,
        "threshold_run_signal_density_band_span_gap_delta_balance_crest(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_crest(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -350,
        "threshold_run_signal_density_band_span_gap_delta_balance_plume(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_plume(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -357,
        "threshold_run_signal_density_band_span_gap_delta_balance_spire(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_spire(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -360,
        "threshold_run_signal_density_band_span_gap_delta_balance_flare(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_flare(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -367,
        "threshold_run_signal_density_band_span_gap_delta_balance_spark(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_spark(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -373,
        "threshold_run_signal_density_band_span_gap_delta_balance_torch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_torch(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -378,
        "threshold_run_signal_density_band_span_gap_delta_balance_ember(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ember(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -390,
        "threshold_run_signal_density_band_span_gap_delta_balance_glow(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_glow(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -398,
        "threshold_run_signal_density_band_span_gap_delta_balance_ash(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ash(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -405,
        "threshold_run_signal_density_band_span_gap_delta_balance_blaze(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_blaze(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -412,
        "threshold_run_signal_density_band_span_gap_delta_balance_flame(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_flame(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -424,
        "threshold_run_signal_density_band_span_gap_delta_balance_smoke(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_smoke(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -427,
        "threshold_run_signal_density_band_span_gap_delta_balance_stone(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_stone(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -435,
        "threshold_run_signal_density_band_span_gap_delta_balance_brand(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_brand(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -442,
        "threshold_run_signal_density_band_span_gap_delta_balance_forge(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_forge(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -454,
        "threshold_run_signal_density_band_span_gap_delta_balance_anvil(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_anvil(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -460,
        "threshold_run_signal_density_band_span_gap_delta_balance_metal(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_metal(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -472,
        "threshold_run_signal_density_band_span_gap_delta_balance_iron(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_iron(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -484,
        "threshold_run_signal_density_band_span_gap_delta_balance_mold(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mold(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -502,
        "threshold_run_signal_density_band_span_gap_delta_balance_cast(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cast(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -509,
        "threshold_run_signal_density_band_span_gap_delta_balance_ore(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ore(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -516,
        "threshold_run_signal_density_band_span_gap_delta_balance_ingot(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ingot(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -529,
        "threshold_run_signal_density_band_span_gap_delta_balance_steel(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_steel(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -535,
        "threshold_run_signal_density_band_span_gap_delta_balance_smelt(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_smelt(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -541,
        "threshold_run_signal_density_band_span_gap_delta_balance_alloy(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_alloy(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -548,
        "threshold_run_signal_density_band_span_gap_delta_balance_fuse(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_fuse(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -555,
        "threshold_run_signal_density_band_span_gap_delta_balance_braze(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_braze(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -567,
        "threshold_run_signal_density_band_span_gap_delta_balance_meld(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_meld(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -575,
        "threshold_run_signal_density_band_span_gap_delta_balance_weld(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_weld(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -582,
        "threshold_run_signal_density_band_span_gap_delta_balance_solder(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_solder(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -589,
        "threshold_run_signal_density_band_span_gap_delta_balance_rivet(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_rivet(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -600,
        "threshold_run_signal_density_band_span_gap_delta_balance_bolt(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bolt(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -603,
        "threshold_run_signal_density_band_span_gap_delta_balance_screw(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_screw(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -615,
        "threshold_run_signal_density_band_span_gap_delta_balance_nail(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_nail(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -622,
        "threshold_run_signal_density_band_span_gap_delta_balance_thread(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_thread(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -629,
        "threshold_run_signal_density_band_span_gap_delta_balance_weave(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_weave(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -641,
        "threshold_run_signal_density_band_span_gap_delta_balance_stitch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_stitch(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -649,
        "threshold_run_signal_density_band_span_gap_delta_balance_lace(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_lace(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -657,
        "threshold_run_signal_density_band_span_gap_delta_balance_cord(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cord(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -669,
        "threshold_run_signal_density_band_span_gap_delta_balance_fiber(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_fiber(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -681,
        "threshold_run_signal_density_band_span_gap_delta_balance_strand(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_strand(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -684,
        "threshold_run_signal_density_band_span_gap_delta_balance_twine(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_twine(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -693,
        "threshold_run_signal_density_band_span_gap_delta_balance_yarn(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_yarn(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -707,
        "threshold_run_signal_density_band_span_gap_delta_balance_loom(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_loom(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -721,
        "threshold_run_signal_density_band_span_gap_delta_balance_braid(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_braid(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -733,
        "threshold_run_signal_density_band_span_gap_delta_balance_mesh(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mesh(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -740,
        "threshold_run_signal_density_band_span_gap_delta_balance_net(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_net(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -743,
        "threshold_run_signal_density_band_span_gap_delta_balance_web(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_web(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -756,
        "threshold_run_signal_density_band_span_gap_delta_balance_grid(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_grid(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -769,
        "threshold_run_signal_density_band_span_gap_delta_balance_cloth(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cloth(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -782,
        "threshold_run_signal_density_band_span_gap_delta_balance_knit(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_knit(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -795,
        "threshold_run_signal_density_band_span_gap_delta_balance_loop(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_loop(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -807,
        "threshold_run_signal_density_band_span_gap_delta_balance_tile(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_tile(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -815,
        "threshold_run_signal_density_band_span_gap_delta_balance_patch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_patch(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -822,
        "threshold_run_signal_density_band_span_gap_delta_balance_seam(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_seam(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -830,
        "threshold_run_signal_density_band_span_gap_delta_balance_node(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_node(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -838,
        "threshold_run_signal_density_band_span_gap_delta_balance_ring(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ring(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -845,
        "threshold_run_signal_density_band_span_gap_delta_balance_bead(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bead(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -852,
        "threshold_run_signal_density_band_span_gap_delta_balance_charm(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_charm(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -860,
        "threshold_run_signal_density_band_span_gap_delta_balance_gem(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_gem(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -867,
        "threshold_run_signal_density_band_span_gap_delta_balance_jewel(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_jewel(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -875,
        "threshold_run_signal_density_band_span_gap_delta_balance_facet(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_facet(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -882,
        "threshold_run_signal_density_band_span_gap_delta_balance_prism(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_prism(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -894,
        "threshold_run_signal_density_band_span_gap_delta_balance_opal(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_opal(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -906,
        "threshold_run_signal_density_band_span_gap_delta_balance_ruby(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ruby(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -909,
        "threshold_run_signal_density_band_span_gap_delta_balance_pearl(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pearl(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -927,
        "threshold_run_signal_density_band_span_gap_delta_balance_agate(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_agate(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -934,
        "threshold_run_signal_density_band_span_gap_delta_balance_topaz(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_topaz(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -941,
        "threshold_run_signal_density_band_span_gap_delta_balance_amber(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_amber(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -953,
        "threshold_run_signal_density_band_span_gap_delta_balance_garnet(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_garnet(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -961,
        "threshold_run_signal_density_band_span_gap_delta_balance_onyx(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_onyx(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -968,
        "threshold_run_signal_density_band_span_gap_delta_balance_quartz(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_quartz(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -980,
        "threshold_run_signal_density_band_span_gap_delta_balance_jade(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_jade(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -988,
        "threshold_run_signal_density_band_span_gap_delta_balance_beryl(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_beryl(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -995,
        "threshold_run_signal_density_band_span_gap_delta_balance_coral(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_coral(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1002,
        "threshold_run_signal_density_band_span_gap_delta_balance_lapis(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_lapis(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1009,
        "threshold_run_signal_density_band_span_gap_delta_balance_zircon(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_zircon(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1016,
        "threshold_run_signal_density_band_span_gap_delta_balance_spinel(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_spinel(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1024,
        "threshold_run_signal_density_band_span_gap_delta_balance_jasper(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_jasper(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1036,
        "threshold_run_signal_density_band_span_gap_delta_balance_marble(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_marble(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1043,
        "threshold_run_signal_density_band_span_gap_delta_balance_basalt(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_basalt(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1055,
        "threshold_run_signal_density_band_span_gap_delta_balance_slate(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_slate(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1067,
        "threshold_run_signal_density_band_span_gap_delta_balance_shale(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_shale(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1074,
        "threshold_run_signal_density_band_span_gap_delta_balance_shard(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_shard(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1082,
        "threshold_run_signal_density_band_span_gap_delta_balance_gravel(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_gravel(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1089,
        "threshold_run_signal_density_band_span_gap_delta_balance_pebble(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pebble(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1096,
        "threshold_run_signal_density_band_span_gap_delta_balance_cobble(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cobble(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1104,
        "threshold_run_signal_density_band_span_gap_delta_balance_rubble(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_rubble(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1111,
        "threshold_run_signal_density_band_span_gap_delta_balance_talus(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_talus(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1118,
        "threshold_run_signal_density_band_span_gap_delta_balance_scree(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_scree(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1125,
        "threshold_run_signal_density_band_span_gap_delta_balance_cairn(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cairn(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1137,
        "threshold_run_signal_density_band_span_gap_delta_balance_mound(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mound(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1144,
        "threshold_run_signal_density_band_span_gap_delta_balance_dune(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_dune(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1152,
        "threshold_run_signal_density_band_span_gap_delta_balance_ridge(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ridge(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1159,
        "threshold_run_signal_density_band_span_gap_delta_balance_ledge(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ledge(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1171,
        "threshold_run_signal_density_band_span_gap_delta_balance_butte(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_butte(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1178,
        "threshold_run_signal_density_band_span_gap_delta_balance_mesa(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mesa(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1190,
        "threshold_run_signal_density_band_span_gap_delta_balance_cliff(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cliff(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1202,
        "threshold_run_signal_density_band_span_gap_delta_balance_crag(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_crag(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1209,
        "threshold_run_signal_density_band_span_gap_delta_balance_canyon(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_canyon(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1216,
        "threshold_run_signal_density_band_span_gap_delta_balance_gully(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_gully(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1224,
        "threshold_run_signal_density_band_span_gap_delta_balance_basin(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_basin(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1231,
        "threshold_run_signal_density_band_span_gap_delta_balance_grove(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_grove(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1243,
        "threshold_run_signal_density_band_span_gap_delta_balance_forest(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_forest(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1250,
        "threshold_run_signal_density_band_span_gap_delta_balance_canopy(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_canopy(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1257,
        "threshold_run_signal_density_band_span_gap_delta_balance_branch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_branch(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1265,
        "threshold_run_signal_density_band_span_gap_delta_balance_leaf(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_leaf(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1272,
        "threshold_run_signal_density_band_span_gap_delta_balance_bough(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bough(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1284,
        "threshold_run_signal_density_band_span_gap_delta_balance_twig(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_twig(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1291,
        "threshold_run_signal_density_band_span_gap_delta_balance_sprout(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_sprout(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1303,
        "threshold_run_signal_density_band_span_gap_delta_balance_bud(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bud(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1311,
        "threshold_run_signal_density_band_span_gap_delta_balance_flower(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_flower(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1318,
        "threshold_run_signal_density_band_span_gap_delta_balance_petal(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_petal(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1325,
        "threshold_run_signal_density_band_span_gap_delta_balance_seed(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_seed(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1337,
        "threshold_run_signal_density_band_span_gap_delta_balance_fruit(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_fruit(clamp([9, 1, 5, 3], 2, 6), 3, 5)": -1344,
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
        ("threshold_transition_density(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_transition_density(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 1),
        ("threshold_transition_balance(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_transition_balance(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -3),
        ("threshold_run_contrast(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_contrast(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 7),
        ("threshold_run_contrast_delta(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_contrast_delta(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 7),
        ("threshold_run_signal_score(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_score(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 11),
        ("threshold_run_signal_density(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 3),
        ("threshold_run_signal_density_delta(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_delta(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 3),
        ("threshold_run_signal_density_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 1),
        ("threshold_run_signal_density_gap(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_gap(clamp([9, 1, 5, 3], 2, 6), 3, 5)", 4),
        ("threshold_run_signal_density_band(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -8),
        ("threshold_run_signal_density_band_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -10),
        ("threshold_run_signal_density_band_gap(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_gap(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -7),
        ("threshold_run_signal_density_band_gap_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_gap_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -9),
        ("threshold_run_signal_density_band_span(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -21),
        ("threshold_run_signal_density_band_span_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -23),
        ("threshold_run_signal_density_band_span_gap(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -20),
        ("threshold_run_signal_density_band_span_gap_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -22),
        ("threshold_run_signal_density_band_span_gap_delta(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -22),
        ("threshold_run_signal_density_band_span_gap_delta_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -24),
        ("threshold_run_signal_density_band_span_gap_delta_balance(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -21),
        ("threshold_run_signal_density_band_span_gap_delta_balance_ratio(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ratio(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -23),
        ("threshold_run_signal_density_band_span_gap_delta_balance_delta(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_delta(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -23),
        ("threshold_run_signal_density_band_span_gap_delta_balance_count(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_count(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -25),
        ("threshold_run_signal_density_band_span_gap_delta_balance_drift(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_drift(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -26),
        ("threshold_run_signal_density_band_span_gap_delta_balance_spread(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_spread(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -38),
        ("threshold_run_signal_density_band_span_gap_delta_balance_mass(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mass(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -44),
        ("threshold_run_signal_density_band_span_gap_delta_balance_load(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_load(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -48),
        ("threshold_run_signal_density_band_span_gap_delta_balance_flux(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_flux(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -49),
        ("threshold_run_signal_density_band_span_gap_delta_balance_wave(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_wave(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -69),
        ("threshold_run_signal_density_band_span_gap_delta_balance_peak(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_peak(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -75),
        ("threshold_run_signal_density_band_span_gap_delta_balance_tail(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_tail(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -81),
        ("threshold_run_signal_density_band_span_gap_delta_balance_edge(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_edge(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -93),
        ("threshold_run_signal_density_band_span_gap_delta_balance_rim(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_rim(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -95),
        ("threshold_run_signal_density_band_span_gap_delta_balance_lip(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_lip(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -96),
        ("threshold_run_signal_density_band_span_gap_delta_balance_jaw(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_jaw(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -104),
        ("threshold_run_signal_density_band_span_gap_delta_balance_bite(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bite(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -117),
        ("threshold_run_signal_density_band_span_gap_delta_balance_grip(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_grip(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -123),
        ("threshold_run_signal_density_band_span_gap_delta_balance_hold(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_hold(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -133),
        ("threshold_run_signal_density_band_span_gap_delta_balance_lock(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_lock(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -136),
        ("threshold_run_signal_density_band_span_gap_delta_balance_seal(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_seal(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -143),
        ("threshold_run_signal_density_band_span_gap_delta_balance_mark(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mark(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -155),
        ("threshold_run_signal_density_band_span_gap_delta_balance_stamp(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_stamp(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -162),
        ("threshold_run_signal_density_band_span_gap_delta_balance_press(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_press(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -169),
        ("threshold_run_signal_density_band_span_gap_delta_balance_pin(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pin(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -177),
        ("threshold_run_signal_density_band_span_gap_delta_balance_snap(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_snap(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -180),
        ("threshold_run_signal_density_band_span_gap_delta_balance_clasp(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_clasp(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -198),
        ("threshold_run_signal_density_band_span_gap_delta_balance_latch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_latch(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -201),
        ("threshold_run_signal_density_band_span_gap_delta_balance_hook(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_hook(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -208),
        ("threshold_run_signal_density_band_span_gap_delta_balance_link(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_link(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -215),
        ("threshold_run_signal_density_band_span_gap_delta_balance_chain(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_chain(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -222),
        ("threshold_run_signal_density_band_span_gap_delta_balance_rope(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_rope(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -235),
        ("threshold_run_signal_density_band_span_gap_delta_balance_knot(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_knot(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -241),
        ("threshold_run_signal_density_band_span_gap_delta_balance_tie(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_tie(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -244),
        ("threshold_run_signal_density_band_span_gap_delta_balance_bow(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bow(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -252),
        ("threshold_run_signal_density_band_span_gap_delta_balance_arc(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_arc(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -259),
        ("threshold_run_signal_density_band_span_gap_delta_balance_arch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_arch(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -272),
        ("threshold_run_signal_density_band_span_gap_delta_balance_gate(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_gate(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -281),
        ("threshold_run_signal_density_band_span_gap_delta_balance_guard(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_guard(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -288),
        ("threshold_run_signal_density_band_span_gap_delta_balance_shield(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_shield(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -294),
        ("threshold_run_signal_density_band_span_gap_delta_balance_wall(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_wall(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -295),
        ("threshold_run_signal_density_band_span_gap_delta_balance_fort(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_fort(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -302),
        ("threshold_run_signal_density_band_span_gap_delta_balance_keep(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_keep(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -306),
        ("threshold_run_signal_density_band_span_gap_delta_balance_core(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_core(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -317),
        ("threshold_run_signal_density_band_span_gap_delta_balance_root(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_root(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -331),
        ("threshold_run_signal_density_band_span_gap_delta_balance_crown(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_crown(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -338),
        ("threshold_run_signal_density_band_span_gap_delta_balance_halo(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_halo(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -343),
        ("threshold_run_signal_density_band_span_gap_delta_balance_crest(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_crest(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -350),
        ("threshold_run_signal_density_band_span_gap_delta_balance_plume(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_plume(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -357),
        ("threshold_run_signal_density_band_span_gap_delta_balance_spire(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_spire(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -360),
        ("threshold_run_signal_density_band_span_gap_delta_balance_flare(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_flare(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -367),
        ("threshold_run_signal_density_band_span_gap_delta_balance_spark(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_spark(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -373),
        ("threshold_run_signal_density_band_span_gap_delta_balance_torch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_torch(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -378),
        ("threshold_run_signal_density_band_span_gap_delta_balance_ember(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ember(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -390),
        ("threshold_run_signal_density_band_span_gap_delta_balance_glow(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_glow(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -398),
        ("threshold_run_signal_density_band_span_gap_delta_balance_ash(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ash(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -405),
        ("threshold_run_signal_density_band_span_gap_delta_balance_blaze(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_blaze(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -412),
        ("threshold_run_signal_density_band_span_gap_delta_balance_flame(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_flame(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -424),
        ("threshold_run_signal_density_band_span_gap_delta_balance_smoke(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_smoke(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -427),
        ("threshold_run_signal_density_band_span_gap_delta_balance_stone(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_stone(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -435),
        ("threshold_run_signal_density_band_span_gap_delta_balance_brand(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_brand(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -442),
        ("threshold_run_signal_density_band_span_gap_delta_balance_forge(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_forge(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -454),
        ("threshold_run_signal_density_band_span_gap_delta_balance_anvil(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_anvil(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -460),
        ("threshold_run_signal_density_band_span_gap_delta_balance_metal(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_metal(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -472),
        ("threshold_run_signal_density_band_span_gap_delta_balance_iron(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_iron(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -484),
        ("threshold_run_signal_density_band_span_gap_delta_balance_mold(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mold(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -502),
        ("threshold_run_signal_density_band_span_gap_delta_balance_cast(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cast(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -509),
        ("threshold_run_signal_density_band_span_gap_delta_balance_ore(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ore(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -516),
        ("threshold_run_signal_density_band_span_gap_delta_balance_ingot(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ingot(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -529),
        ("threshold_run_signal_density_band_span_gap_delta_balance_steel(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_steel(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -535),
        ("threshold_run_signal_density_band_span_gap_delta_balance_smelt(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_smelt(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -541),
        ("threshold_run_signal_density_band_span_gap_delta_balance_alloy(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_alloy(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -548),
        ("threshold_run_signal_density_band_span_gap_delta_balance_fuse(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_fuse(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -555),
        ("threshold_run_signal_density_band_span_gap_delta_balance_braze(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_braze(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -567),
        ("threshold_run_signal_density_band_span_gap_delta_balance_meld(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_meld(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -575),
        ("threshold_run_signal_density_band_span_gap_delta_balance_weld(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_weld(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -582),
        ("threshold_run_signal_density_band_span_gap_delta_balance_solder(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_solder(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -589),
        ("threshold_run_signal_density_band_span_gap_delta_balance_rivet(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_rivet(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -600),
        ("threshold_run_signal_density_band_span_gap_delta_balance_bolt(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bolt(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -603),
        ("threshold_run_signal_density_band_span_gap_delta_balance_screw(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_screw(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -615),
        ("threshold_run_signal_density_band_span_gap_delta_balance_nail(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_nail(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -622),
        ("threshold_run_signal_density_band_span_gap_delta_balance_thread(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_thread(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -629),
        ("threshold_run_signal_density_band_span_gap_delta_balance_weave(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_weave(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -641),
        ("threshold_run_signal_density_band_span_gap_delta_balance_stitch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_stitch(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -649),
        ("threshold_run_signal_density_band_span_gap_delta_balance_lace(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_lace(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -657),
        ("threshold_run_signal_density_band_span_gap_delta_balance_cord(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cord(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -669),
        ("threshold_run_signal_density_band_span_gap_delta_balance_fiber(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_fiber(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -681),
        ("threshold_run_signal_density_band_span_gap_delta_balance_strand(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_strand(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -684),
        ("threshold_run_signal_density_band_span_gap_delta_balance_twine(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_twine(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -693),
        ("threshold_run_signal_density_band_span_gap_delta_balance_yarn(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_yarn(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -707),
        ("threshold_run_signal_density_band_span_gap_delta_balance_loom(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_loom(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -721),
        ("threshold_run_signal_density_band_span_gap_delta_balance_braid(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_braid(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -733),
        ("threshold_run_signal_density_band_span_gap_delta_balance_mesh(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mesh(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -740),
        ("threshold_run_signal_density_band_span_gap_delta_balance_net(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_net(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -743),
        ("threshold_run_signal_density_band_span_gap_delta_balance_web(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_web(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -756),
        ("threshold_run_signal_density_band_span_gap_delta_balance_grid(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_grid(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -769),
        ("threshold_run_signal_density_band_span_gap_delta_balance_cloth(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cloth(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -782),
        ("threshold_run_signal_density_band_span_gap_delta_balance_knit(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_knit(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -795),
        ("threshold_run_signal_density_band_span_gap_delta_balance_loop(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_loop(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -807),
        ("threshold_run_signal_density_band_span_gap_delta_balance_tile(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_tile(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -815),
        ("threshold_run_signal_density_band_span_gap_delta_balance_patch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_patch(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -822),
        ("threshold_run_signal_density_band_span_gap_delta_balance_seam(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_seam(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -830),
        ("threshold_run_signal_density_band_span_gap_delta_balance_node(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_node(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -838),
        ("threshold_run_signal_density_band_span_gap_delta_balance_ring(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ring(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -845),
        ("threshold_run_signal_density_band_span_gap_delta_balance_bead(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bead(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -852),
        ("threshold_run_signal_density_band_span_gap_delta_balance_charm(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_charm(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -860),
        ("threshold_run_signal_density_band_span_gap_delta_balance_gem(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_gem(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -867),
        ("threshold_run_signal_density_band_span_gap_delta_balance_jewel(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_jewel(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -875),
        ("threshold_run_signal_density_band_span_gap_delta_balance_facet(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_facet(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -882),
        ("threshold_run_signal_density_band_span_gap_delta_balance_prism(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_prism(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -894),
        ("threshold_run_signal_density_band_span_gap_delta_balance_opal(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_opal(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -906),
        ("threshold_run_signal_density_band_span_gap_delta_balance_ruby(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ruby(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -909),
        ("threshold_run_signal_density_band_span_gap_delta_balance_pearl(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pearl(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -927),
        ("threshold_run_signal_density_band_span_gap_delta_balance_agate(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_agate(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -934),
        ("threshold_run_signal_density_band_span_gap_delta_balance_topaz(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_topaz(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -941),
        ("threshold_run_signal_density_band_span_gap_delta_balance_amber(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_amber(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -953),
        ("threshold_run_signal_density_band_span_gap_delta_balance_garnet(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_garnet(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -961),
        ("threshold_run_signal_density_band_span_gap_delta_balance_onyx(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_onyx(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -968),
        ("threshold_run_signal_density_band_span_gap_delta_balance_quartz(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_quartz(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -980),
        ("threshold_run_signal_density_band_span_gap_delta_balance_jade(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_jade(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -988),
        ("threshold_run_signal_density_band_span_gap_delta_balance_beryl(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_beryl(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -995),
        ("threshold_run_signal_density_band_span_gap_delta_balance_coral(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_coral(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1002),
        ("threshold_run_signal_density_band_span_gap_delta_balance_lapis(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_lapis(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1009),
        ("threshold_run_signal_density_band_span_gap_delta_balance_zircon(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_zircon(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1016),
        ("threshold_run_signal_density_band_span_gap_delta_balance_spinel(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_spinel(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1024),
        ("threshold_run_signal_density_band_span_gap_delta_balance_jasper(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_jasper(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1036),
        ("threshold_run_signal_density_band_span_gap_delta_balance_marble(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_marble(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1043),
        ("threshold_run_signal_density_band_span_gap_delta_balance_basalt(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_basalt(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1055),
        ("threshold_run_signal_density_band_span_gap_delta_balance_slate(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_slate(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1067),
        ("threshold_run_signal_density_band_span_gap_delta_balance_shale(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_shale(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1074),
        ("threshold_run_signal_density_band_span_gap_delta_balance_shard(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_shard(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1082),
        ("threshold_run_signal_density_band_span_gap_delta_balance_gravel(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_gravel(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1089),
        ("threshold_run_signal_density_band_span_gap_delta_balance_pebble(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pebble(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1096),
        ("threshold_run_signal_density_band_span_gap_delta_balance_cobble(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cobble(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1104),
        ("threshold_run_signal_density_band_span_gap_delta_balance_rubble(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_rubble(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1111),
        ("threshold_run_signal_density_band_span_gap_delta_balance_talus(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_talus(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1118),
        ("threshold_run_signal_density_band_span_gap_delta_balance_scree(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_scree(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1125),
        ("threshold_run_signal_density_band_span_gap_delta_balance_cairn(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cairn(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1137),
        ("threshold_run_signal_density_band_span_gap_delta_balance_mound(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mound(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1144),
        ("threshold_run_signal_density_band_span_gap_delta_balance_dune(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_dune(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1152),
        ("threshold_run_signal_density_band_span_gap_delta_balance_ridge(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ridge(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1159),
        ("threshold_run_signal_density_band_span_gap_delta_balance_ledge(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_ledge(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1171),
        ("threshold_run_signal_density_band_span_gap_delta_balance_butte(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_butte(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1178),
        ("threshold_run_signal_density_band_span_gap_delta_balance_mesa(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mesa(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1190),
        ("threshold_run_signal_density_band_span_gap_delta_balance_cliff(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cliff(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1202),
        ("threshold_run_signal_density_band_span_gap_delta_balance_crag(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_crag(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1209),
        ("threshold_run_signal_density_band_span_gap_delta_balance_canyon(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_canyon(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1216),
        ("threshold_run_signal_density_band_span_gap_delta_balance_gully(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_gully(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1224),
        ("threshold_run_signal_density_band_span_gap_delta_balance_basin(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_basin(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1231),
        ("threshold_run_signal_density_band_span_gap_delta_balance_grove(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_grove(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1243),
        ("threshold_run_signal_density_band_span_gap_delta_balance_forest(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_forest(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1250),
        ("threshold_run_signal_density_band_span_gap_delta_balance_canopy(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_canopy(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1257),
        ("threshold_run_signal_density_band_span_gap_delta_balance_branch(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_branch(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1265),
        ("threshold_run_signal_density_band_span_gap_delta_balance_leaf(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_leaf(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1272),
        ("threshold_run_signal_density_band_span_gap_delta_balance_bough(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bough(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1284),
        ("threshold_run_signal_density_band_span_gap_delta_balance_twig(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_twig(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1291),
        ("threshold_run_signal_density_band_span_gap_delta_balance_sprout(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_sprout(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1303),
        ("threshold_run_signal_density_band_span_gap_delta_balance_bud(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bud(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1311),
        ("threshold_run_signal_density_band_span_gap_delta_balance_flower(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_flower(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1318),
        ("threshold_run_signal_density_band_span_gap_delta_balance_petal(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_petal(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1325),
        ("threshold_run_signal_density_band_span_gap_delta_balance_seed(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_seed(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1337),
        ("threshold_run_signal_density_band_span_gap_delta_balance_fruit(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_fruit(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1344),
        ("threshold_run_signal_density_band_span_gap_delta_balance_tree(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_tree(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1356),
        ("threshold_run_signal_density_band_span_gap_delta_balance_trunk(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_trunk(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1363),
        ("threshold_run_signal_density_band_span_gap_delta_balance_bark(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bark(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1371),
        ("threshold_run_signal_density_band_span_gap_delta_balance_limb(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_limb(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1378),
        ("threshold_run_signal_density_band_span_gap_delta_balance_stump(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_stump(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1390),
        ("threshold_run_signal_density_band_span_gap_delta_balance_sap(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_sap(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1402),
        ("threshold_run_signal_density_band_span_gap_delta_balance_shoot(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_shoot(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1409),
        ("threshold_run_signal_density_band_span_gap_delta_balance_stem(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_stem(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1417),
        ("threshold_run_signal_density_band_span_gap_delta_balance_sprig(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_sprig(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1424),
        ("threshold_run_signal_density_band_span_gap_delta_balance_frond(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_frond(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1431),
        ("threshold_run_signal_density_band_span_gap_delta_balance_fern(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_fern(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1439),
        ("threshold_run_signal_density_band_span_gap_delta_balance_moss(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_moss(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1446),
        ("threshold_run_signal_density_band_span_gap_delta_balance_lichen(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_lichen(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1458),
        ("threshold_run_signal_density_band_span_gap_delta_balance_algae(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_algae(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1470),
        ("threshold_run_signal_density_band_span_gap_delta_balance_kelp(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_kelp(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1477),
        ("threshold_run_signal_density_band_span_gap_delta_balance_reed(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_reed(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1489),
        ("threshold_run_signal_density_band_span_gap_delta_balance_rush(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_rush(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1496),
        ("threshold_run_signal_density_band_span_gap_delta_balance_brook(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_brook(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1503),
        ("threshold_run_signal_density_band_span_gap_delta_balance_stream(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_stream(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1515),
        ("threshold_run_signal_density_band_span_gap_delta_balance_creek(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_creek(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1527),
        ("threshold_run_signal_density_band_span_gap_delta_balance_river(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_river(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1534),
        ("threshold_run_signal_density_band_span_gap_delta_balance_pond(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pond(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1542),
        ("threshold_run_signal_density_band_span_gap_delta_balance_lake(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_lake(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1549),
        ("threshold_run_signal_density_band_span_gap_delta_balance_lagoon(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_lagoon(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1561),
        ("threshold_run_signal_density_band_span_gap_delta_balance_marsh(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_marsh(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1568),
        ("threshold_run_signal_density_band_span_gap_delta_balance_swamp(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_swamp(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1580),
        ("threshold_run_signal_density_band_span_gap_delta_balance_bog(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bog(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1592),
        ("threshold_run_signal_density_band_span_gap_delta_balance_fen(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_fen(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1599),
        ("threshold_run_signal_density_band_span_gap_delta_balance_mere(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mere(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1611),
        ("threshold_run_signal_density_band_span_gap_delta_balance_pool(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pool(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1619),
        ("threshold_run_signal_density_band_span_gap_delta_balance_cove(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_cove(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1626),
        ("threshold_run_signal_density_band_span_gap_delta_balance_bay(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_bay(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1638),
        ("threshold_run_signal_density_band_span_gap_delta_balance_harbor(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_harbor(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1650),
        ("threshold_run_signal_density_band_span_gap_delta_balance_inlet(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_inlet(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1658),
        ("threshold_run_signal_density_band_span_gap_delta_balance_port(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_port(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1665),
        ("threshold_run_signal_density_band_span_gap_delta_balance_dock(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_dock(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1677),
        ("threshold_run_signal_density_band_span_gap_delta_balance_pier(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pier(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1689),
        ("threshold_run_signal_density_band_span_gap_delta_balance_quay(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_quay(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1696),
        ("threshold_run_signal_density_band_span_gap_delta_balance_wharf(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_wharf(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1704),
        ("threshold_run_signal_density_band_span_gap_delta_balance_berth(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_berth(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1716),
        ("threshold_run_signal_density_band_span_gap_delta_balance_buoy(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_buoy(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1728),
        ("threshold_run_signal_density_band_span_gap_delta_balance_float(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_float(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1735),
        ("threshold_run_signal_density_band_span_gap_delta_balance_raft(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_raft(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1743),
        ("threshold_run_signal_density_band_span_gap_delta_balance_sail(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_sail(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1750),
        ("threshold_run_signal_density_band_span_gap_delta_balance_mast(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_mast(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1762),
        ("threshold_run_signal_density_band_span_gap_delta_balance_helm(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_helm(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1769),
        ("threshold_run_signal_density_band_span_gap_delta_balance_rudder(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_rudder(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1777),
        ("threshold_run_signal_density_band_span_gap_delta_balance_tiller(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_tiller(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1789),
        ("threshold_run_signal_density_band_span_gap_delta_balance_wheel(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_wheel(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1796),
        ("threshold_run_signal_density_band_span_gap_delta_balance_axle(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_axle(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1804),
        ("threshold_run_signal_density_band_span_gap_delta_balance_hub(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_hub(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1811),
        ("threshold_run_signal_density_band_span_gap_delta_balance_spoke(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_spoke(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1823),
        ("threshold_run_signal_density_band_span_gap_delta_balance_tire(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_tire(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1830),
        ("threshold_run_signal_density_band_span_gap_delta_balance_tread(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_tread(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1842),
        ("threshold_run_signal_density_band_span_gap_delta_balance_track(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_track(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1850),
        ("threshold_run_signal_density_band_span_gap_delta_balance_road(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_road(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1857),
        ("threshold_run_signal_density_band_span_gap_delta_balance_lane(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_lane(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1864),
        ("threshold_run_signal_density_band_span_gap_delta_balance_route(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_route(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1876),
        ("threshold_run_signal_density_band_span_gap_delta_balance_path(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_path(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1884),
        ("threshold_run_signal_density_band_span_gap_delta_balance_trail(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_trail(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1891),
        ("threshold_run_signal_density_band_span_gap_delta_balance_walk(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_walk(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1903),
        ("threshold_run_signal_density_band_span_gap_delta_balance_step(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_step(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1915),
        ("threshold_run_signal_density_band_span_gap_delta_balance_stride(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_stride(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1927),
        ("threshold_run_signal_density_band_span_gap_delta_balance_pace(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pace(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1934),
        ("threshold_run_signal_density_band_span_gap_delta_balance_gait(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_gait(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1942),
        ("threshold_run_signal_density_band_span_gap_delta_balance_tempo(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_tempo(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1954),
        ("threshold_run_signal_density_band_span_gap_delta_balance_rhythm(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_rhythm(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1961),
        ("threshold_run_signal_density_band_span_gap_delta_balance_pulse(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_pulse(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1973),
        ("threshold_run_signal_density_band_span_gap_delta_balance_beat(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_beat(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1980),
        ("threshold_run_signal_density_band_span_gap_delta_balance_meter(clamp([9, 1, 5, 3], 2, 6), 2, 6) + outlier_run_signal_density_band_span_gap_delta_balance_meter(clamp([9, 1, 5, 3], 2, 6), 3, 5)", -1988),
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
        "threshold_transition_density(1, 0, 1)": "expected array",
        "threshold_transition_density([1], [0], 1)": "expected integer",
        "threshold_transition_density([1], 0, [1])": "expected integer",
        "threshold_transition_density([1], 0)": "wrong argument count",
        "outlier_transition_density(1, 0, 1)": "expected array",
        "outlier_transition_density([1], [0], 1)": "expected integer",
        "outlier_transition_density([1], 0, [1])": "expected integer",
        "outlier_transition_density([1], 0)": "wrong argument count",
        "threshold_transition_balance(1, 0, 1)": "expected array",
        "threshold_transition_balance([1], [0], 1)": "expected integer",
        "threshold_transition_balance([1], 0, [1])": "expected integer",
        "threshold_transition_balance([1], 0)": "wrong argument count",
        "outlier_transition_balance(1, 0, 1)": "expected array",
        "outlier_transition_balance([1], [0], 1)": "expected integer",
        "outlier_transition_balance([1], 0, [1])": "expected integer",
        "outlier_transition_balance([1], 0)": "wrong argument count",
        "threshold_run_contrast(1, 0, 1)": "expected array",
        "threshold_run_contrast([1], [0], 1)": "expected integer",
        "threshold_run_contrast([1], 0, [1])": "expected integer",
        "threshold_run_contrast([1], 0)": "wrong argument count",
        "threshold_run_contrast_delta(1, 0, 1)": "expected array",
        "threshold_run_contrast_delta([1], [0], 1)": "expected integer",
        "threshold_run_contrast_delta([1], 0, [1])": "expected integer",
        "threshold_run_contrast_delta([1], 0)": "wrong argument count",
        "outlier_run_contrast_delta(1, 0, 1)": "expected array",
        "outlier_run_contrast_delta([1], [0], 1)": "expected integer",
        "outlier_run_contrast_delta([1], 0, [1])": "expected integer",
        "outlier_run_contrast_delta([1], 0)": "wrong argument count",
        "threshold_run_signal_score(1, 0, 1)": "expected array",
        "threshold_run_signal_score([1], [0], 1)": "expected integer",
        "threshold_run_signal_score([1], 0, [1])": "expected integer",
        "threshold_run_signal_score([1], 0)": "wrong argument count",
        "outlier_run_signal_score(1, 0, 1)": "expected array",
        "outlier_run_signal_score([1], [0], 1)": "expected integer",
        "outlier_run_signal_score([1], 0, [1])": "expected integer",
        "outlier_run_signal_score([1], 0)": "wrong argument count",
        "threshold_run_signal_density(1, 0, 1)": "expected array",
        "threshold_run_signal_density([1], [0], 1)": "expected integer",
        "threshold_run_signal_density([1], 0, [1])": "expected integer",
        "threshold_run_signal_density([1], 0)": "wrong argument count",
        "outlier_run_signal_density(1, 0, 1)": "expected array",
        "outlier_run_signal_density([1], [0], 1)": "expected integer",
        "outlier_run_signal_density([1], 0, [1])": "expected integer",
        "outlier_run_signal_density([1], 0)": "wrong argument count",
        "threshold_run_signal_density_delta(1, 0, 1)": "expected array",
        "threshold_run_signal_density_delta([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_delta([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_delta([1], 0)": "wrong argument count",
        "outlier_run_signal_density_delta(1, 0, 1)": "expected array",
        "outlier_run_signal_density_delta([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_delta([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_delta([1], 0)": "wrong argument count",
        "threshold_run_signal_density_ratio(1, 0, 1)": "expected array",
        "threshold_run_signal_density_ratio([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_ratio([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_ratio([1], 0)": "wrong argument count",
        "outlier_run_signal_density_ratio(1, 0, 1)": "expected array",
        "outlier_run_signal_density_ratio([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_ratio([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_ratio([1], 0)": "wrong argument count",
        "threshold_run_signal_density_gap(1, 0, 1)": "expected array",
        "threshold_run_signal_density_gap([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_gap([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_gap([1], 0)": "wrong argument count",
        "outlier_run_signal_density_gap(1, 0, 1)": "expected array",
        "outlier_run_signal_density_gap([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_gap([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_gap([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_ratio(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_ratio([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_ratio([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_ratio([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_ratio(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_ratio([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_ratio([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_ratio([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_gap(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_gap([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_gap([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_gap([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_gap(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_gap([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_gap([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_gap([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_gap_ratio(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_gap_ratio([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_gap_ratio([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_gap_ratio([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_gap_ratio(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_gap_ratio([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_gap_ratio([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_gap_ratio([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_ratio(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_ratio([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_ratio([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_ratio([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_ratio(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_ratio([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_ratio([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_ratio([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_ratio(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_ratio([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_ratio([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_ratio([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_ratio(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_ratio([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_ratio([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_ratio([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_ratio(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_ratio([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_ratio([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_ratio([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_ratio(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_ratio([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_ratio([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_ratio([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_ratio(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_ratio([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ratio([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ratio([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_ratio(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_ratio([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ratio([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ratio([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_delta(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_delta([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_delta([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_delta([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_delta(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_delta([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_delta([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_delta([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_count(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_count([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_count([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_count([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_count(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_count([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_count([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_count([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_drift(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_drift([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_drift([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_drift([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_drift(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_drift([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_drift([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_drift([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_spread(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_spread([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_spread([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_spread([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_spread(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_spread([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_spread([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_spread([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_mass(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_mass([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mass([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mass([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_mass(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_mass([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mass([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mass([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_load(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_load([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_load([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_load([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_load(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_load([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_load([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_load([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_flux(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_flux([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_flux([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_flux([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_flux(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_flux([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_flux([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_flux([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_wave(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_wave([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_wave([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_wave([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_wave(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_wave([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_wave([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_wave([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_peak(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_peak([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_peak([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_peak([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_peak(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_peak([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_peak([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_peak([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_tail(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_tail([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tail([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tail([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_tail(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_tail([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tail([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tail([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_edge(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_edge([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_edge([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_edge([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_edge(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_edge([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_edge([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_edge([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_rim(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_rim([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rim([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rim([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_rim(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_rim([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rim([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rim([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_lip(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_lip([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lip([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lip([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_lip(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_lip([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lip([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lip([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_jaw(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_jaw([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_jaw([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_jaw([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_jaw(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_jaw([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_jaw([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_jaw([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_bite(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_bite([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bite([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bite([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_bite(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_bite([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bite([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bite([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_grip(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_grip([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_grip([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_grip([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_grip(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_grip([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_grip([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_grip([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_hold(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_hold([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_hold([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_hold([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_hold(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_hold([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_hold([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_hold([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_lock(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_lock([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lock([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lock([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_lock(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_lock([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lock([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lock([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_seal(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_seal([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_seal([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_seal([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_seal(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_seal([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_seal([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_seal([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_mark(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_mark([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mark([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mark([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_mark(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_mark([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mark([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mark([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_stamp(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_stamp([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stamp([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stamp([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_stamp(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_stamp([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stamp([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stamp([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_press(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_press([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_press([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_press([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_press(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_press([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_press([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_press([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_pin(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_pin([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pin([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pin([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_pin(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_pin([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pin([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pin([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_snap(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_snap([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_snap([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_snap([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_snap(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_snap([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_snap([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_snap([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_clasp(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_clasp([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_clasp([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_clasp([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_clasp(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_clasp([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_clasp([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_clasp([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_latch(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_latch([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_latch([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_latch([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_latch(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_latch([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_latch([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_latch([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_hook(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_hook([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_hook([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_hook([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_hook(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_hook([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_hook([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_hook([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_link(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_link([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_link([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_link([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_link(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_link([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_link([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_link([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_chain(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_chain([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_chain([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_chain([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_chain(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_chain([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_chain([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_chain([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_rope(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_rope([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rope([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rope([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_rope(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_rope([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rope([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rope([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_knot(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_knot([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_knot([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_knot([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_knot(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_knot([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_knot([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_knot([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_tie(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_tie([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tie([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tie([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_tie(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_tie([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tie([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tie([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_bow(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_bow([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bow([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bow([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_bow(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_bow([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bow([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bow([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_arc(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_arc([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_arc([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_arc([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_arc(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_arc([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_arc([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_arc([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_arch(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_arch([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_arch([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_arch([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_arch(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_arch([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_arch([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_arch([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_gate(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_gate([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_gate([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_gate([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_gate(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_gate([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_gate([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_gate([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_guard(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_guard([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_guard([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_guard([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_guard(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_guard([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_guard([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_guard([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_shield(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_shield([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_shield([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_shield([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_shield(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_shield([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_shield([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_shield([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_wall(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_wall([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_wall([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_wall([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_wall(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_wall([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_wall([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_wall([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_fort(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_fort([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fort([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fort([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_fort(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_fort([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fort([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fort([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_keep(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_keep([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_keep([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_keep([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_keep(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_keep([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_keep([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_keep([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_core(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_core([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_core([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_core([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_core(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_core([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_core([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_core([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_root(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_root([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_root([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_root([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_root(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_root([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_root([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_root([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_crown(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_crown([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_crown([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_crown([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_crown(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_crown([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_crown([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_crown([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_halo(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_halo([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_halo([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_halo([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_halo(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_halo([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_halo([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_halo([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_crest(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_crest([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_crest([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_crest([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_crest(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_crest([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_crest([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_crest([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_plume(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_plume([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_plume([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_plume([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_plume(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_plume([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_plume([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_plume([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_spire(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_spire([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_spire([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_spire([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_spire(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_spire([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_spire([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_spire([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_flare(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_flare([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_flare([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_flare([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_flare(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_flare([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_flare([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_flare([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_spark(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_spark([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_spark([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_spark([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_spark(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_spark([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_spark([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_spark([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_torch(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_torch([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_torch([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_torch([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_torch(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_torch([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_torch([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_torch([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_ember(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_ember([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ember([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ember([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_ember(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_ember([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ember([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ember([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_glow(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_glow([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_glow([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_glow([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_glow(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_glow([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_glow([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_glow([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_ash(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_ash([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ash([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ash([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_ash(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_ash([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ash([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ash([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_blaze(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_blaze([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_blaze([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_blaze([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_blaze(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_blaze([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_blaze([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_blaze([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_flame(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_flame([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_flame([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_flame([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_flame(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_flame([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_flame([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_flame([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_smoke(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_smoke([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_smoke([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_smoke([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_smoke(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_smoke([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_smoke([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_smoke([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_stone(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_stone([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stone([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stone([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_stone(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_stone([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stone([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stone([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_brand(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_brand([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_brand([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_brand([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_brand(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_brand([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_brand([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_brand([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_forge(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_forge([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_forge([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_forge([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_forge(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_forge([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_forge([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_forge([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_anvil(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_anvil([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_anvil([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_anvil([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_anvil(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_anvil([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_anvil([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_anvil([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_metal(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_metal([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_metal([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_metal([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_metal(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_metal([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_metal([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_metal([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_iron(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_iron([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_iron([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_iron([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_iron(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_iron([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_iron([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_iron([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_mold(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_mold([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mold([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mold([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_mold(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_mold([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mold([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mold([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_cast(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_cast([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cast([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cast([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_cast(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_cast([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cast([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cast([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_ore(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_ore([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ore([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ore([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_ore(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_ore([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ore([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ore([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_ingot(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_ingot([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ingot([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ingot([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_ingot(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_ingot([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ingot([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ingot([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_steel(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_steel([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_steel([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_steel([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_steel(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_steel([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_steel([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_steel([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_smelt(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_smelt([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_smelt([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_smelt([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_smelt(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_smelt([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_smelt([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_smelt([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_alloy(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_alloy([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_alloy([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_alloy([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_alloy(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_alloy([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_alloy([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_alloy([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_fuse(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_fuse([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fuse([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fuse([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_fuse(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_fuse([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fuse([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fuse([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_braze(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_braze([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_braze([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_braze([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_braze(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_braze([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_braze([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_braze([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_meld(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_meld([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_meld([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_meld([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_meld(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_meld([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_meld([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_meld([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_weld(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_weld([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_weld([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_weld([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_weld(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_weld([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_weld([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_weld([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_solder(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_solder([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_solder([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_solder([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_solder(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_solder([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_solder([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_solder([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_rivet(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_rivet([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rivet([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rivet([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_rivet(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_rivet([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rivet([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rivet([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_bolt(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_bolt([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bolt([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bolt([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_bolt(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_bolt([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bolt([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bolt([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_screw(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_screw([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_screw([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_screw([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_screw(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_screw([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_screw([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_screw([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_nail(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_nail([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_nail([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_nail([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_nail(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_nail([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_nail([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_nail([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_thread(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_thread([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_thread([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_thread([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_thread(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_thread([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_thread([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_thread([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_weave(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_weave([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_weave([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_weave([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_weave(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_weave([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_weave([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_weave([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_stitch(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_stitch([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stitch([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stitch([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_stitch(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_stitch([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stitch([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stitch([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_lace(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_lace([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lace([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lace([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_lace(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_lace([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lace([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lace([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_cord(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_cord([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cord([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cord([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_cord(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_cord([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cord([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cord([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_fiber(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_fiber([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fiber([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fiber([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_fiber(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_fiber([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fiber([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fiber([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_strand(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_strand([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_strand([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_strand([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_strand(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_strand([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_strand([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_strand([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_twine(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_twine([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_twine([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_twine([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_twine(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_twine([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_twine([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_twine([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_yarn(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_yarn([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_yarn([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_yarn([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_yarn(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_yarn([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_yarn([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_yarn([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_loom(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_loom([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_loom([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_loom([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_loom(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_loom([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_loom([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_loom([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_braid(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_braid([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_braid([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_braid([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_braid(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_braid([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_braid([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_braid([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_mesh(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_mesh([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mesh([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mesh([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_mesh(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_mesh([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mesh([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mesh([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_net(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_net([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_net([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_net([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_net(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_net([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_net([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_net([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_web(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_web([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_web([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_web([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_web(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_web([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_web([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_web([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_grid(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_grid([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_grid([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_grid([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_grid(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_grid([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_grid([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_grid([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_cloth(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_cloth([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cloth([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cloth([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_cloth(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_cloth([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cloth([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cloth([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_knit(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_knit([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_knit([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_knit([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_knit(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_knit([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_knit([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_knit([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_loop(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_loop([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_loop([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_loop([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_loop(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_loop([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_loop([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_loop([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_tile(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_tile([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tile([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tile([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_tile(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_tile([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tile([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tile([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_patch(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_patch([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_patch([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_patch([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_patch(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_patch([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_patch([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_patch([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_seam(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_seam([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_seam([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_seam([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_seam(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_seam([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_seam([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_seam([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_node(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_node([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_node([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_node([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_node(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_node([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_node([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_node([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_ring(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_ring([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ring([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ring([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_ring(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_ring([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ring([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ring([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_bead(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_bead([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bead([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bead([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_bead(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_bead([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bead([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bead([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_charm(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_charm([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_charm([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_charm([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_charm(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_charm([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_charm([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_charm([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_gem(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_gem([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_gem([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_gem([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_gem(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_gem([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_gem([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_gem([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_jewel(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_jewel([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_jewel([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_jewel([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_jewel(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_jewel([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_jewel([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_jewel([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_facet(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_facet([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_facet([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_facet([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_facet(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_facet([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_facet([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_facet([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_prism(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_prism([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_prism([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_prism([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_prism(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_prism([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_prism([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_prism([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_opal(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_opal([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_opal([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_opal([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_opal(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_opal([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_opal([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_opal([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_ruby(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_ruby([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ruby([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ruby([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_ruby(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_ruby([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ruby([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ruby([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_pearl(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_pearl([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pearl([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pearl([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_pearl(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_pearl([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pearl([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pearl([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_agate(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_agate([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_agate([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_agate([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_agate(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_agate([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_agate([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_agate([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_topaz(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_topaz([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_topaz([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_topaz([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_topaz(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_topaz([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_topaz([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_topaz([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_amber(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_amber([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_amber([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_amber([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_amber(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_amber([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_amber([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_amber([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_garnet(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_garnet([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_garnet([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_garnet([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_garnet(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_garnet([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_garnet([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_garnet([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_onyx(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_onyx([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_onyx([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_onyx([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_onyx(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_onyx([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_onyx([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_onyx([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_quartz(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_quartz([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_quartz([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_quartz([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_quartz(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_quartz([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_quartz([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_quartz([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_jade(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_jade([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_jade([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_jade([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_jade(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_jade([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_jade([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_jade([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_beryl(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_beryl([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_beryl([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_beryl([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_beryl(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_beryl([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_beryl([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_beryl([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_coral(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_coral([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_coral([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_coral([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_coral(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_coral([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_coral([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_coral([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_lapis(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_lapis([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lapis([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lapis([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_lapis(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_lapis([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lapis([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lapis([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_zircon(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_zircon([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_zircon([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_zircon([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_zircon(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_zircon([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_zircon([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_zircon([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_spinel(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_spinel([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_spinel([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_spinel([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_spinel(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_spinel([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_spinel([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_spinel([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_jasper(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_jasper([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_jasper([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_jasper([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_jasper(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_jasper([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_jasper([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_jasper([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_marble(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_marble([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_marble([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_marble([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_marble(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_marble([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_marble([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_marble([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_basalt(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_basalt([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_basalt([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_basalt([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_basalt(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_basalt([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_basalt([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_basalt([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_slate(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_slate([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_slate([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_slate([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_slate(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_slate([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_slate([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_slate([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_shale(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_shale([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_shale([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_shale([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_shale(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_shale([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_shale([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_shale([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_shard(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_shard([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_shard([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_shard([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_shard(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_shard([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_shard([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_shard([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_gravel(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_gravel([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_gravel([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_gravel([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_gravel(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_gravel([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_gravel([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_gravel([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_pebble(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_pebble([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pebble([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pebble([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_pebble(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_pebble([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pebble([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pebble([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_cobble(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_cobble([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cobble([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cobble([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_cobble(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_cobble([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cobble([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cobble([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_rubble(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_rubble([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rubble([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rubble([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_rubble(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_rubble([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rubble([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rubble([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_talus(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_talus([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_talus([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_talus([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_talus(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_talus([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_talus([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_talus([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_scree(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_scree([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_scree([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_scree([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_scree(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_scree([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_scree([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_scree([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_cairn(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_cairn([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cairn([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cairn([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_cairn(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_cairn([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cairn([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cairn([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_mound(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_mound([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mound([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mound([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_mound(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_mound([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mound([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mound([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_dune(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_dune([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_dune([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_dune([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_dune(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_dune([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_dune([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_dune([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_ridge(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_ridge([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ridge([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ridge([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_ridge(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_ridge([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ridge([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ridge([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_ledge(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_ledge([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ledge([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_ledge([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_ledge(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_ledge([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ledge([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_ledge([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_butte(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_butte([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_butte([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_butte([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_butte(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_butte([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_butte([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_butte([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_mesa(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_mesa([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mesa([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mesa([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_mesa(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_mesa([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mesa([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mesa([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_cliff(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_cliff([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cliff([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cliff([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_cliff(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_cliff([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cliff([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cliff([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_crag(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_crag([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_crag([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_crag([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_crag(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_crag([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_crag([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_crag([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_canyon(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_canyon([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_canyon([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_canyon([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_canyon(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_canyon([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_canyon([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_canyon([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_gully(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_gully([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_gully([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_gully([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_gully(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_gully([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_gully([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_gully([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_basin(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_basin([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_basin([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_basin([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_basin(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_basin([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_basin([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_basin([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_grove(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_grove([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_grove([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_grove([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_grove(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_grove([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_grove([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_grove([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_forest(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_forest([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_forest([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_forest([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_forest(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_forest([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_forest([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_forest([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_canopy(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_canopy([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_canopy([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_canopy([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_canopy(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_canopy([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_canopy([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_canopy([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_branch(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_branch([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_branch([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_branch([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_branch(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_branch([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_branch([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_branch([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_leaf(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_leaf([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_leaf([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_leaf([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_leaf(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_leaf([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_leaf([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_leaf([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_bough(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_bough([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bough([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bough([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_bough(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_bough([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bough([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bough([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_twig(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_twig([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_twig([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_twig([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_twig(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_twig([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_twig([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_twig([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_sprout(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_sprout([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_sprout([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_sprout([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_sprout(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_sprout([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_sprout([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_sprout([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_bud(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_bud([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bud([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bud([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_bud(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_bud([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bud([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bud([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_flower(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_flower([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_flower([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_flower([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_flower(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_flower([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_flower([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_flower([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_petal(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_petal([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_petal([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_petal([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_petal(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_petal([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_petal([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_petal([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_seed(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_seed([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_seed([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_seed([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_seed(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_seed([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_seed([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_seed([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_fruit(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_fruit([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fruit([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fruit([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_fruit(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_fruit([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fruit([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fruit([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_tree(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_tree([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tree([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tree([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_tree(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_tree([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tree([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tree([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_trunk(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_trunk([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_trunk([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_trunk([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_trunk(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_trunk([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_trunk([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_trunk([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_bark(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_bark([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bark([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bark([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_bark(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_bark([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bark([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bark([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_limb(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_limb([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_limb([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_limb([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_limb(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_limb([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_limb([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_limb([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_stump(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_stump([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stump([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stump([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_stump(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_stump([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stump([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stump([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_sap(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_sap([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_sap([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_sap([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_sap(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_sap([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_sap([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_sap([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_shoot(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_shoot([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_shoot([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_shoot([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_shoot(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_shoot([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_shoot([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_shoot([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_stem(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_stem([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stem([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stem([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_stem(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_stem([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stem([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stem([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_sprig(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_sprig([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_sprig([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_sprig([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_sprig(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_sprig([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_sprig([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_sprig([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_frond(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_frond([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_frond([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_frond([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_frond(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_frond([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_frond([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_frond([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_fern(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_fern([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fern([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fern([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_fern(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_fern([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fern([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fern([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_moss(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_moss([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_moss([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_moss([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_moss(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_moss([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_moss([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_moss([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_lichen(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_lichen([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lichen([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lichen([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_lichen(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_lichen([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lichen([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lichen([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_algae(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_algae([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_algae([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_algae([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_algae(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_algae([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_algae([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_algae([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_kelp(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_kelp([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_kelp([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_kelp([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_kelp(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_kelp([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_kelp([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_kelp([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_reed(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_reed([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_reed([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_reed([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_reed(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_reed([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_reed([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_reed([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_rush(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_rush([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rush([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rush([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_rush(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_rush([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rush([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rush([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_brook(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_brook([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_brook([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_brook([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_brook(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_brook([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_brook([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_brook([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_stream(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_stream([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stream([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stream([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_stream(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_stream([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stream([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stream([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_creek(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_creek([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_creek([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_creek([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_creek(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_creek([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_creek([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_creek([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_river(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_river([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_river([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_river([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_river(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_river([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_river([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_river([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_pond(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_pond([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pond([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pond([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_pond(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_pond([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pond([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pond([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_lake(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_lake([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lake([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lake([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_lake(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_lake([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lake([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lake([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_lagoon(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_lagoon([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lagoon([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lagoon([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_lagoon(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_lagoon([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lagoon([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lagoon([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_marsh(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_marsh([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_marsh([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_marsh([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_marsh(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_marsh([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_marsh([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_marsh([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_swamp(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_swamp([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_swamp([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_swamp([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_swamp(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_swamp([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_swamp([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_swamp([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_bog(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_bog([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bog([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bog([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_bog(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_bog([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bog([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bog([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_fen(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_fen([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fen([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_fen([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_fen(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_fen([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fen([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_fen([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_mere(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_mere([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mere([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mere([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_mere(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_mere([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mere([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mere([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_pool(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_pool([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pool([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pool([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_pool(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_pool([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pool([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pool([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_cove(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_cove([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cove([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_cove([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_cove(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_cove([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cove([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_cove([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_bay(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_bay([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bay([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_bay([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_bay(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_bay([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bay([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_bay([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_harbor(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_harbor([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_harbor([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_harbor([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_harbor(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_harbor([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_harbor([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_harbor([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_inlet(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_inlet([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_inlet([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_inlet([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_inlet(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_inlet([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_inlet([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_inlet([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_port(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_port([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_port([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_port([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_port(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_port([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_port([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_port([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_dock(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_dock([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_dock([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_dock([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_dock(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_dock([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_dock([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_dock([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_pier(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_pier([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pier([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pier([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_pier(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_pier([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pier([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pier([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_quay(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_quay([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_quay([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_quay([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_quay(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_quay([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_quay([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_quay([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_wharf(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_wharf([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_wharf([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_wharf([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_wharf(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_wharf([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_wharf([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_wharf([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_berth(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_berth([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_berth([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_berth([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_berth(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_berth([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_berth([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_berth([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_buoy(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_buoy([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_buoy([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_buoy([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_buoy(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_buoy([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_buoy([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_buoy([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_float(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_float([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_float([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_float([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_float(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_float([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_float([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_float([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_raft(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_raft([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_raft([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_raft([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_raft(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_raft([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_raft([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_raft([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_sail(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_sail([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_sail([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_sail([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_sail(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_sail([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_sail([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_sail([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_mast(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_mast([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mast([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_mast([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_mast(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_mast([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mast([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_mast([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_helm(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_helm([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_helm([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_helm([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_helm(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_helm([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_helm([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_helm([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_rudder(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_rudder([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rudder([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rudder([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_rudder(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_rudder([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rudder([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rudder([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_tiller(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_tiller([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tiller([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tiller([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_tiller(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_tiller([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tiller([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tiller([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_wheel(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_wheel([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_wheel([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_wheel([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_wheel(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_wheel([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_wheel([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_wheel([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_axle(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_axle([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_axle([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_axle([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_axle(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_axle([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_axle([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_axle([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_hub(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_hub([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_hub([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_hub([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_hub(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_hub([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_hub([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_hub([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_spoke(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_spoke([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_spoke([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_spoke([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_spoke(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_spoke([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_spoke([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_spoke([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_tire(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_tire([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tire([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tire([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_tire(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_tire([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tire([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tire([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_tread(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_tread([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tread([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tread([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_tread(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_tread([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tread([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tread([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_track(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_track([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_track([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_track([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_track(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_track([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_track([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_track([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_road(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_road([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_road([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_road([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_road(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_road([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_road([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_road([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_lane(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_lane([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lane([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_lane([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_lane(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_lane([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lane([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_lane([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_route(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_route([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_route([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_route([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_route(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_route([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_route([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_route([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_path(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_path([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_path([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_path([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_path(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_path([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_path([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_path([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_trail(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_trail([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_trail([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_trail([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_trail(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_trail([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_trail([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_trail([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_walk(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_walk([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_walk([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_walk([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_walk(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_walk([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_walk([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_walk([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_step(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_step([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_step([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_step([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_step(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_step([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_step([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_step([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_stride(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_stride([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stride([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_stride([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_stride(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_stride([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stride([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_stride([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_pace(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_pace([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pace([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pace([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_pace(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_pace([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pace([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pace([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_gait(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_gait([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_gait([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_gait([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_gait(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_gait([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_gait([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_gait([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_tempo(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_tempo([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tempo([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_tempo([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_tempo(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_tempo([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tempo([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_tempo([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_rhythm(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_rhythm([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rhythm([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_rhythm([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_pulse(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_pulse([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pulse([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_pulse([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_beat(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_beat([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_beat([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_beat([1], 0)": "wrong argument count",
        "threshold_run_signal_density_band_span_gap_delta_balance_meter(1, 0, 1)": "expected array",
        "threshold_run_signal_density_band_span_gap_delta_balance_meter([1], [0], 1)": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_meter([1], 0, [1])": "expected integer",
        "threshold_run_signal_density_band_span_gap_delta_balance_meter([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_rhythm(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_rhythm([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rhythm([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_rhythm([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_pulse(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_pulse([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pulse([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_pulse([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_beat(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_beat([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_beat([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_beat([1], 0)": "wrong argument count",
        "outlier_run_signal_density_band_span_gap_delta_balance_meter(1, 0, 1)": "expected array",
        "outlier_run_signal_density_band_span_gap_delta_balance_meter([1], [0], 1)": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_meter([1], 0, [1])": "expected integer",
        "outlier_run_signal_density_band_span_gap_delta_balance_meter([1], 0)": "wrong argument count",
        "outlier_run_contrast(1, 0, 1)": "expected array",
        "outlier_run_contrast([1], [0], 1)": "expected integer",
        "outlier_run_contrast([1], 0, [1])": "expected integer",
        "outlier_run_contrast([1], 0)": "wrong argument count",
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
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_transition_density([3, 4, 7, 3, 5, 9, 4], 3, 6); n = n + 1; }; total": 65,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_transition_density([3, 4, 7, 3, 5, 9, 4], 3, 6); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_transition_balance([3, 4, 7, 3, 5, 9, 4], 3, 6); n = n + 1; }; total": -65,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_transition_balance([3, 4, 7, 3, 5, 9, 4], 3, 6); n = n + 1; }; total": 130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_contrast([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": 325,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_contrast_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_contrast([1, 3, 8, 9, 10, 5, 0], 3, 6); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_score([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": 390,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_score([1, 3, 8, 9, 10, 5, 0], 3, 6); n = n + 1; }; total": 195,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": 65,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": 65,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -65,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_delta([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": 0,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -260,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_ratio([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_gap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -130,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_gap([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": 0,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_gap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -455,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_gap([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -325,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_gap_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -650,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_gap_ratio([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -455,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -910,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -780,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -1105,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_ratio([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -910,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -975,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -780,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -1365,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_ratio([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -910,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -1495,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_ratio([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -1105,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_ratio([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -1560,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_ratio([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -1105,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_delta([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -1690,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_delta([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -1170,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_count([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -1885,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_count([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -1300,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_drift([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -2145,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_drift([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -1430,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_spread([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -2405,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_spread([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -1755,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_mass([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -2795,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_mass([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -2080,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_load([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -2990,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_load([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -2275,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_flux([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -3250,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_flux([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -2405,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_wave([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -3445,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_wave([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -2795,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_peak([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -3640,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_peak([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -2990,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_tail([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -3705,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_tail([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -3120,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_edge([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -3965,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_edge([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -3445,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_rim([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -4160,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_rim([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -3575,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_lip([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -4420,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_lip([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -3705,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_jaw([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -5005,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_jaw([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -4160,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_bite([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -5525,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_bite([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -4615,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_grip([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -5915,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_grip([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -4940,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_hold([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -6500,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_hold([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -5460,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_lock([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -6955,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_lock([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -5720,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_seal([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -7605,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_seal([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -6175,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_mark([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -8385,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_mark([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -6825,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_stamp([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -8840,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_stamp([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -7150,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_press([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -9165,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_press([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -7410,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_pin([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -9425,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_pin([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -7670,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_snap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -9880,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_snap([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -7930,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_clasp([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -10530,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_clasp([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -8580,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_latch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -10985,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_latch([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -8840,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_hook([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -11440,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_hook([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -9165,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_link([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -11765,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_link([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -9425,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_chain([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -12415,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_chain([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -9880,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_rope([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -12935,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_rope([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -10335,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_knot([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -13325,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_knot([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -10660,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_tie([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -13780,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_tie([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -10920,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_bow([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -14170,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_bow([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -11245,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_arc([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -14495,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_arc([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -11505,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_arch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -15015,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_arch([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -11960,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_gate([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -15860,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_gate([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -12545,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_guard([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -16510,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_guard([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -13000,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_shield([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -16900,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_shield([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -13325,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_wall([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -17160,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_wall([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -13455,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_fort([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -17810,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_fort([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -13910,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_keep([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -18005,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_keep([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -14105,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_core([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -18850,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_core([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -14755,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_root([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -19305,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_root([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -15210,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_crown([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -19955,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_crown([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -15665,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_halo([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -20410,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_halo([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -15990,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_crest([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -20865,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_crest([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -16315,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_plume([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -21190,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_plume([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -16575,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_spire([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -21645,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_spire([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -16835,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_flare([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -22295,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_flare([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -17290,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_spark([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -22685,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_spark([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -17615,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_torch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -23140,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_torch([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -17940,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_ember([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -23595,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_ember([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -18395,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_glow([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -23985,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_glow([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -18720,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_ash([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -24310,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_ash([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -18980,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_blaze([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -24765,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_blaze([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -19305,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_flame([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -25350,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_flame([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -19825,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_smoke([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -25805,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_smoke([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -20085,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_stone([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -26390,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_stone([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -20540,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_brand([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -27040,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_brand([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -20995,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_forge([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -27625,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_forge([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -21515,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_anvil([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -27690,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_anvil([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -21645,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_metal([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -28145,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_metal([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -22100,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_iron([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -28405,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_iron([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -22425,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_mold([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -29055,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_mold([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -23075,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_cast([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -29705,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_cast([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -23530,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_ore([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -30160,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_ore([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -23855,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_ingot([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -31005,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_ingot([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -24505,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_steel([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -31070,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_steel([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -24635,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_smelt([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -31460,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_smelt([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -24960,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_alloy([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -31785,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_alloy([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -25220,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_fuse([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -32435,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_fuse([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -25675,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_braze([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -32695,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_braze([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -26000,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_meld([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -33280,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_meld([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -26455,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_weld([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -33930,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_weld([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -26910,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_solder([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -34255,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_solder([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -27170,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_rivet([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -34840,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_rivet([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -27690,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_bolt([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -35295,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_bolt([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -27950,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_screw([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -35750,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_screw([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -28405,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_nail([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -36205,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_nail([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -28730,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_thread([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -36855,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_thread([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -29185,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_weave([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -37115,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_weave([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -29510,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_stitch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -37700,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_stitch([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -29965,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_lace([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -37960,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_lace([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -30225,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_cord([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -38545,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_cord([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -30745,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_fiber([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -39000,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_fiber([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -31200,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_strand([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -39455,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_strand([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -31460,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_twine([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -40300,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_twine([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -32045,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_yarn([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -41080,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_yarn([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -32695,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_loom([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -41730,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_loom([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -33280,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_braid([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -41990,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_braid([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -33605,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_mesh([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -42640,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_mesh([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -34060,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_net([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -43095,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_net([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -34320,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_web([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -43940,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_web([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -34970,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_grid([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -44655,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_grid([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -35555,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_cloth([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -45500,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_cloth([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -36205,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_knit([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -46215,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_knit([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -36790,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_loop([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -46475,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_loop([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -37115,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_tile([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -47060,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_tile([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -37570,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_patch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -47710,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_patch([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -38025,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_seam([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -48100,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_seam([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -38350,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_node([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -48360,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_node([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -38610,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_ring([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -49010,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_ring([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -39065,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_bead([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -49465,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_bead([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -39390,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_charm([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -50050,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_charm([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -39845,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_gem([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -50700,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_gem([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -40300,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_jewel([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -51090,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_jewel([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -40625,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_facet([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -51415,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_facet([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -40885,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_prism([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -52000,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_prism([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -41405,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_opal([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -52455,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_opal([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -41860,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_ruby([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -52910,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_ruby([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -42120,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_pearl([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -53560,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_pearl([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -42770,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_agate([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -54210,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_agate([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -43225,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_topaz([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -54665,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_topaz([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -43550,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_amber([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -55120,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_amber([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -44005,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_garnet([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -55510,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_garnet([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -44330,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_onyx([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -56160,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_onyx([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -44785,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_quartz([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -56420,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_quartz([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -45110,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_jade([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -57005,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_jade([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -45565,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_beryl([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -57655,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_beryl([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -46020,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_coral([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -58110,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_coral([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -46345,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_lapis([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -58435,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_lapis([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -46605,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_zircon([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -59085,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_zircon([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -47060,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_spinel([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -59475,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_spinel([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -47385,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_jasper([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -59930,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_jasper([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -47840,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_marble([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -60580,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_marble([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -48295,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_basalt([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -61165,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_basalt([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -48815,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_slate([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -61620,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_slate([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -49270,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_shale([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -62270,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_shale([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -49725,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_shard([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -62660,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_shard([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -50050,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_gravel([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -63310,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_gravel([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -50505,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_pebble([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -63765,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_pebble([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -50830,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_cobble([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -64350,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_cobble([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -51285,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_rubble([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -65000,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_rubble([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -51740,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_talus([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -65455,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_talus([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -52065,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_scree([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -65780,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_scree([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -52325,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_cairn([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -66235,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_cairn([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -52780,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_mound([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -66885,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_mound([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -53235,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_dune([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -67275,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_dune([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -53560,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_ridge([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -67925,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_ridge([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -54015,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_ledge([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -68185,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_ledge([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -54340,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_butte([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -68835,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_butte([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -54795,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_mesa([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -69420,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_mesa([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -55315,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_cliff([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -69875,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_cliff([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -55770,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_crag([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -70525,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_crag([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -56225,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_canyon([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -70980,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_canyon([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -56550,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_gully([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -71565,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_gully([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -57005,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_basin([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -72215,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_basin([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -57460,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_grove([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -72475,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_grove([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -57785,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_forest([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -73125,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_forest([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -58240,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_canopy([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -73580,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_canopy([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -58565,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_branch([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -74165,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_branch([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -59020,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_leaf([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -74815,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_leaf([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -59475,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_bough([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -75075,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_bough([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -59800,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_twig([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -75725,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_twig([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -60255,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_sprout([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -76310,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_sprout([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -60775,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_bud([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -76570,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_bud([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -61035,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_flower([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -77220,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_flower([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -61490,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_petal([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -77675,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_petal([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -61815,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_seed([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -78130,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_seed([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -62270,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_fruit([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -78780,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_fruit([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -62725,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_tree([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -79365,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_tree([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -63245,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_trunk([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -80015,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_trunk([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -63700,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_bark([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -80600,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_bark([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -64155,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_limb([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -81250,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_limb([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -64610,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_stump([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -81835,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_stump([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -65130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_sap([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -82290,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_sap([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -65585,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_shoot([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -82940,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_shoot([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -66040,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_stem([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -83330,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_stem([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -66365,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_sprig([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -83980,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_sprig([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -66820,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_frond([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -84435,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_frond([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -67145,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_fern([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -85020,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_fern([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -67600,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_moss([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -85670,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_moss([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -68055,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_lichen([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -86255,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_lichen([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -68575,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_algae([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -86710,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_algae([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -69030,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_kelp([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -87360,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_kelp([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -69485,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_reed([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -87945,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_reed([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -70005,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_rush([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -88270,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_rush([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -70265,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_brook([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -88920,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_brook([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -70720,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_stream([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -89505,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_stream([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -71240,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_creek([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -89960,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_creek([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -71695,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_river([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -90610,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_river([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -72150,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_pond([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -91195,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_pond([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -72605,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_lake([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -91650,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_lake([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -72930,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_lagoon([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -92105,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_lagoon([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -73385,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_marsh([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -92755,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_marsh([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -73840,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_swamp([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -93340,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_swamp([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -74360,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_bog([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -93795,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_bog([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -74815,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_fen([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -94445,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_fen([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -75270,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_mere([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -95030,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_mere([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -75790,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_pool([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -95615,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_pool([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -76245,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_cove([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -96265,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_cove([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -76700,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_bay([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -96850,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_bay([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -77220,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_harbor([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -97305,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_harbor([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -77675,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_inlet([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -97890,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_inlet([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -78130,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_port([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -98540,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_port([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -78585,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_dock([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -99125,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_dock([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -79105,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_pier([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -99580,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_pier([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -79560,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_quay([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -100230,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_quay([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -80015,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_wharf([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -100815,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_wharf([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -80470,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_berth([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -101400,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_berth([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -80990,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_buoy([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -101855,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_buoy([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -81445,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_float([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -102505,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_float([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -81900,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_raft([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -103090,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_raft([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -82355,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_sail([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -103545,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_sail([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -82680,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_mast([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -104000,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_mast([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -83135,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_helm([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -104650,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_helm([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -83590,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_rudder([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -105040,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_rudder([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -83915,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_tiller([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -105495,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_tiller([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -84370,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_wheel([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -105950,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_wheel([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -84695,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_axle([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -106535,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_axle([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -85150,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_hub([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -106860,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_hub([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -85410,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_spoke([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -107445,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_spoke([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -85930,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_tire([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -108095,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_tire([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -86385,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_tread([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -108355,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_tread([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -86710,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_track([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -108940,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_track([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -87165,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_road([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -109590,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_road([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -87620,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_lane([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -110045,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_lane([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -87945,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_route([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -110500,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_route([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -88400,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_path([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -111085,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_path([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -88855,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_trail([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -111735,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_trail([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -89310,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_walk([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -111995,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_walk([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -89635,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_step([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -112580,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_step([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -90155,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_stride([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -113035,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_stride([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -90610,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_pace([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -113685,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_pace([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -91065,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_gait([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -114075,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_gait([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -91390,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_tempo([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -114530,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_tempo([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -91845,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_rhythm([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -114855,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_rhythm([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -92105,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_pulse([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -115440,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_pulse([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -92625,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_beat([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -116090,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_beat([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -93080,
        "let n = 0; let total = 0; while n < 65 { total = total + threshold_run_signal_density_band_span_gap_delta_balance_meter([3, 4, 7, 3, 5, 6, 9, 4], 3, 6); n = n + 1; }; total": -116675,
        "let n = 0; let total = 0; while n < 65 { total = total + outlier_run_signal_density_band_span_gap_delta_balance_meter([1, 8, 9, 3, 0, 1], 3, 6); n = n + 1; }; total": -93535,
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
