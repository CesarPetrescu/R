#include "rustic.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    long out = 123;
    char source[128];

    if (rustic_eval_expression("let x = 2 + 3; x * 4", &out) != RUSTIC_OK || out != 20) {
        return 1;
    }
    if (rustic_eval_expression("999999999999999999999999999999999999999", &out) !=
            RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 2;
    }
    if (strcmp(rustic_status_message(RUSTIC_ERR_INTEGER_OVERFLOW), "integer overflow") != 0) {
        return 3;
    }
    if (snprintf(source, sizeof(source), "let x = %ld; x + 1", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 6;
    }
    if (snprintf(source, sizeof(source), "let x = 0 - %ld - 1; x / -1", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 7;
    }
    if (snprintf(source, sizeof(source), "sum([%ld, 1])", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 8;
    }
    if (snprintf(source, sizeof(source), "prefix_sum([%ld, 1])[1]", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 9;
    }
    if (snprintf(source, sizeof(source), "window_sum([%ld, 1], 2)[0]", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 10;
    }
    if (snprintf(source, sizeof(source), "moving_average_sum([%ld, 1], 2)[0]", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 11;
    }
    if (snprintf(source, sizeof(source), "chunk_sum([%ld, 1], 2)[0]", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 12;
    }
    if (snprintf(source, sizeof(source), "adjacent_diff([-1, %ld])[1]", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 13;
    }
    if (snprintf(source, sizeof(source), "variance_sum([%ld, 1])", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 14;
    }
    if (snprintf(source, sizeof(source), "median([%ld, %ld])", LONG_MAX, LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 15;
    }
    if (snprintf(source, sizeof(source), "top_sum([%ld, 1], 2)", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 16;
    }
    if (snprintf(source, sizeof(source), "fn id(x) { x }; weighted_score([%ld, 1], id)", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 17;
    }
    if (snprintf(source, sizeof(source), "histogram_pairs_score([%ld], [2])", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 18;
    }
    if (snprintf(source, sizeof(source), "histogram_pairs_score([%ld, 1], [1, 1])", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 19;
    }
    if (snprintf(source, sizeof(source), "histogram_distance_score([1], [0 - %ld - 1], [])", LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 20;
    }
    if (snprintf(source, sizeof(source), "histogram_within_distance([1], [%ld], [2], %ld)", LONG_MAX, LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 21;
    }
    if (snprintf(source, sizeof(source), "outlier_score([-1], %ld, %ld)", LONG_MAX, LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 22;
    }
    if (snprintf(source, sizeof(source), "outlier_score([0, 0], %ld, %ld)", LONG_MAX, LONG_MAX) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 23;
    }
    {
        char nested[2050];
        size_t i;
        for (i = 0; i < 1024; i++) {
            nested[i] = '(';
            nested[1025 + i] = ')';
        }
        nested[1024] = '1';
        nested[2049] = '\0';
        if (rustic_eval_expression(nested, &out) != RUSTIC_ERR_STEP_LIMIT_EXCEEDED || out != 20) {
            return 24;
        }
        if (rustic_eval_expression("2 + 3", &out) != RUSTIC_OK || out != 5) {
            return 25;
        }
        out = 20;
    }
    {
        char name[65];
        memset(name, 'a', 64);
        name[64] = '\0';
        if (snprintf(source, sizeof(source), "let %s = 5; 1", name) < 0 ||
                rustic_eval_expression(source, &out) != RUSTIC_ERR_IDENTIFIER_TOO_LONG || out != 20) {
            return 26;
        }
    }
    if (strcmp(rustic_status_message(RUSTIC_ERR_IDENTIFIER_TOO_LONG), "identifier too long") != 0) {
        return 27;
    }
    if (rustic_eval_expression("2 + 3", &out) != RUSTIC_OK || out != 5) {
        return 28;
    }
    out = 20;
    if (snprintf(source, sizeof(source), "match 1 { 1 => 9, -%lu => 0 }",
                 (unsigned long)LONG_MAX + 2UL) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 29;
    }
    if (snprintf(source, sizeof(source), "let low = 0 - %ld - 1; match low { -%lu => 31, _ => 0 }",
                 LONG_MAX, (unsigned long)LONG_MAX + 1UL) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_OK || out != 31) {
        return 30;
    }
    if (snprintf(source, sizeof(source), "let low = -%lu; low / 2", (unsigned long)LONG_MAX + 1UL) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_OK || out != LONG_MIN / 2) {
        return 31;
    }
    out = 20;
    if (snprintf(source, sizeof(source), "-%lu", (unsigned long)LONG_MAX + 2UL) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 32;
    }
    if (snprintf(source, sizeof(source), "--%lu", (unsigned long)LONG_MAX + 1UL) < 0 ||
            rustic_eval_expression(source, &out) != RUSTIC_ERR_INTEGER_OVERFLOW || out != 20) {
        return 33;
    }
    if (rustic_eval_expression("2 + 3", &out) != RUSTIC_OK || out != 5) {
        return 34;
    }
    out = 20;
    if (rustic_eval_expression("3 > 2 > 1", &out) != RUSTIC_ERR_EXPECTED_OPERATOR || out != 20 ||
            strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_OPERATOR), "expected operator") != 0) {
        return 35;
    }
    if (rustic_eval_expression("0 && 1 < 2 < 3", &out) != RUSTIC_ERR_EXPECTED_OPERATOR || out != 20) {
        return 36;
    }
    if (rustic_eval_expression("(3 > 2) == 1", &out) != RUSTIC_OK || out != 1) {
        return 37;
    }
    out = 20;
    {
        char match_source[8192];
        size_t used;
        size_t i;
        int written = snprintf(match_source, sizeof(match_source), "match 0 { ");
        if (written < 0 || (size_t)written >= sizeof(match_source)) {
            return 38;
        }
        used = (size_t)written;
        for (i = 0; i < 520; i++) {
            written = snprintf(match_source + used, sizeof(match_source) - used, "%zu => 1, ", i + 1);
            if (written < 0 || (size_t)written >= sizeof(match_source) - used) {
                return 39;
            }
            used += (size_t)written;
        }
        written = snprintf(match_source + used, sizeof(match_source) - used, "_ => 7 }");
        if (written < 0 || (size_t)written >= sizeof(match_source) - used ||
                rustic_eval_expression(match_source, &out) != RUSTIC_ERR_STEP_LIMIT_EXCEEDED || out != 20) {
            return 40;
        }
    }
    out = 20;
    if (rustic_eval_expression("while 0 { 1 } !0", &out) != RUSTIC_ERR_EXPECTED_SEMICOLON || out != 20) {
        return 43;
    }
    if (rustic_eval_expression("while 0 { 1 } -2", &out) != RUSTIC_ERR_EXPECTED_SEMICOLON || out != 20) {
        return 44;
    }
    if (rustic_eval_expression("while 0 { 1 } [2][0]", &out) != RUSTIC_ERR_EXPECTED_SEMICOLON || out != 20) {
        return 45;
    }
    if (rustic_eval_expression("1 (2)", &out) != RUSTIC_ERR_EXPECTED_SEMICOLON || out != 20 ||
            strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_SEMICOLON), "expected semicolon") != 0) {
        return 42;
    }
    if (rustic_eval_expression("match 0 { 0 => 7, _ => 8 }", &out) != RUSTIC_OK || out != 7) {
        return 41;
    }
    out = 20;
    if (rustic_eval_expression("fn choose(x, y, x) { x }; choose(1, 2, 3)", &out) !=
            RUSTIC_ERR_DUPLICATE_PARAMETER || out != 20 ||
            strcmp(rustic_status_message(RUSTIC_ERR_DUPLICATE_PARAMETER), "duplicate parameter") != 0) {
        return 48;
    }
    if (rustic_eval_expression("fn choose(x, y) { y }; choose(1, 2)", &out) != RUSTIC_OK || out != 2) {
        return 49;
    }
    out = 20;
    {
        char skipped[2048];
        size_t used;
        size_t i;
        int written = snprintf(skipped, sizeof(skipped), "while 1 { break; ");
        if (written < 0 || (size_t)written >= sizeof(skipped)) {
            return 48;
        }
        used = (size_t)written;
        for (i = 0; i < 600; i++) {
            written = snprintf(skipped + used, sizeof(skipped) - used, "0; ");
            if (written < 0 || (size_t)written >= sizeof(skipped) - used) {
                return 49;
            }
            used += (size_t)written;
        }
        written = snprintf(skipped + used, sizeof(skipped) - used, "}; 9");
        if (written < 0 || (size_t)written >= sizeof(skipped) - used ||
                rustic_eval_expression(skipped, &out) != RUSTIC_ERR_STEP_LIMIT_EXCEEDED || out != 20) {
            return 50;
        }
    }
    if (rustic_eval_expression("while 1 { break; { 3 }; 9 }; 7", &out) != RUSTIC_OK || out != 7) {
        return 51;
    }
    if (rustic_eval_expression("sum([1, 2,])", &out) != RUSTIC_OK || out != 3) {
        return 54;
    }
    if (rustic_eval_expression("[1,,][0]", &out) != RUSTIC_ERR_EXPECTED_INTEGER || out != 3) {
        return 55;
    }
    if (rustic_eval_expression("0 && [1, 2,]", &out) != RUSTIC_OK || out != 0) {
        return 56;
    }
    out = 20;
    {
        char skipped[2048];
        size_t used;
        int written = snprintf(skipped, sizeof(skipped), "while 1 { if 1 { break; } else { ");
        if (written < 0 || (size_t)written + 1024 + 16 >= sizeof(skipped)) {
            return 52;
        }
        used = (size_t)written;
        memset(skipped + used, ' ', 1024);
        used += 1024;
        written = snprintf(skipped + used, sizeof(skipped) - used, "0 }; 7 }; 9");
        if (written < 0 || (size_t)written >= sizeof(skipped) - used ||
                rustic_eval_expression(skipped, &out) != RUSTIC_ERR_STEP_LIMIT_EXCEEDED || out != 20) {
            return 53;
        }
    }
    if (rustic_eval_expression("0 && missing(1,,)", &out) != RUSTIC_ERR_EXPECTED_INTEGER || out != 20) {
        return 58;
    }
    if (rustic_eval_expression("fn add(a, b) { a + b }; add(2, 3,)", &out) != RUSTIC_OK || out != 5) {
        return 59;
    }
    out = 20;
    if (rustic_eval_expression("sum([1],,)", &out) != RUSTIC_ERR_EXPECTED_INTEGER || out != 20) {
        return 60;
    }
    if (rustic_eval_expression("[9][len(push([0], 1))-2]", &out) != RUSTIC_OK || out != 9) {
        return 61;
    }
    if (rustic_eval_expression("[9][len(push([0], 1))-1]", &out) !=
            RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS || out != 9) {
        return 62;
    }
    if (rustic_eval_expression("[9][len(push([0], 1))-2]", &out) != RUSTIC_OK || out != 9) {
        return 63;
    }
    out = 20;
    if (rustic_eval_expression("match 0 { 0 => 7, _ => 8, _ => 9 }", &out) !=
            RUSTIC_ERR_DUPLICATE_MATCH_DEFAULT || out != 20 ||
            strcmp(rustic_status_message(RUSTIC_ERR_DUPLICATE_MATCH_DEFAULT), "duplicate match default") != 0) {
        return 64;
    }
    if (rustic_eval_expression("match 0 { 0 => 7, 0 => 8 }", &out) !=
            RUSTIC_ERR_DUPLICATE_MATCH_PATTERN || out != 20 ||
            strcmp(rustic_status_message(RUSTIC_ERR_DUPLICATE_MATCH_PATTERN), "duplicate match pattern") != 0) {
        return 66;
    }
    if (rustic_eval_expression("match 0 { _ => 6 }", &out) != RUSTIC_OK || out != 6) {
        return 65;
    }
    out = 20;
    if (rustic_eval_expression("fn f() { 1 }; fn f() { 2 }; f()", &out) !=
            RUSTIC_ERR_DUPLICATE_FUNCTION || out != 20 ||
            strcmp(rustic_status_message(RUSTIC_ERR_DUPLICATE_FUNCTION), "duplicate function") != 0) {
        return 67;
    }
    if (rustic_eval_expression("fn f() { 1 }; { fn f() { 2 }; f() } + f()", &out) != RUSTIC_OK || out != 3) {
        return 68;
    }
    out = 20;
    if (rustic_eval_expression("let xs = [1]; xs[1] = 9; xs[0]", &out) !=
            RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS || out != 20) {
        return 69;
    }
    if (rustic_eval_expression("let xs = [1]; xs[0] = [2]", &out) !=
            RUSTIC_ERR_EXPECTED_INTEGER || out != 20) {
        return 70;
    }
    if (rustic_eval_expression("let xs = [1]; xs[0] = 9; xs[0]", &out) != RUSTIC_OK || out != 9) {
        return 71;
    }
    out = 20;
    if (rustic_eval_expression("let n = 4; n[0]", &out) != RUSTIC_ERR_EXPECTED_ARRAY || out != 20 ||
            strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_ARRAY), "expected array") != 0) {
        return 72;
    }
    if (rustic_eval_expression("4[1 / 0]", &out) != RUSTIC_ERR_DIVISION_BY_ZERO || out != 20) {
        return 73;
    }
    if (rustic_eval_expression("[9][1]", &out) != RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS || out != 20) {
        return 74;
    }
    if (rustic_eval_expression("[9][0]", &out) != RUSTIC_OK || out != 9) {
        return 75;
    }
    out = 20;
    if (rustic_eval_expression("let if = 5; 7", &out) != RUSTIC_ERR_RESERVED_IDENTIFIER || out != 20 ||
            strcmp(rustic_status_message(RUSTIC_ERR_RESERVED_IDENTIFIER), "reserved identifier") != 0) {
        return 76;
    }
    if (rustic_eval_expression("fn use(match) { match }; 9", &out) != RUSTIC_ERR_RESERVED_IDENTIFIER || out != 20) {
        return 77;
    }
    if (rustic_eval_expression("let if_value = 5; if_value", &out) != RUSTIC_OK || out != 5) {
        return 78;
    }
    out = 20;
    if (rustic_eval_expression(NULL, &out) != RUSTIC_ERR_EXPECTED_INTEGER || out != 20) {
        return 4;
    }
    if (rustic_eval_expression("1", NULL) != RUSTIC_ERR_EXPECTED_INTEGER) {
        return 5;
    }
    puts("C API success, overflow, output preservation and NULL diagnostics: ok");
    return 0;
}
