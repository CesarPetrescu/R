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
            "fn clamp(n) { if n < 0 || n > 10 { 0 } else { n } }; clamp(7) + clamp(12)",
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
