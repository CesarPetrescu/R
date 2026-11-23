#include "rustic.h"

#include <stdio.h>
#include <string.h>

static int check_span(const char *name, const char *source, size_t length,
                      RusticStatus expected_status, long expected_value) {
    long out = -123;
    RusticStatus status = rustic_eval_expression_n(source, length, &out);
    if (status != expected_status || out != expected_value) {
        fprintf(stderr, "%s: expected %s / %ld, got %s / %ld\n", name,
                rustic_status_message(expected_status), expected_value,
                rustic_status_message(status), out);
        return 0;
    }
    return 1;
}

int main(void) {
    enum { LIMIT = 65536 };
    const char source[] = {'6', ' ', '*', ' ', '7'};
    const char larger_buffer[] = "42*";
    const char with_nul[] = {'4', '2', '\0', '*'};
    const char skipped_nul[] = "if 0 { \0 } else { 7 }";
    const char program[] = "fn twice(x){x * 2}; let xs=[20,21]; twice(xs[1])";
    static char at_limit[LIMIT];
    long out = -123;

    memset(at_limit, ' ', sizeof(at_limit));
    at_limit[0] = '1';
    if (!check_span("nonterminated program", source, sizeof(source), RUSTIC_OK, 42) ||
        !check_span("prefix of larger buffer", larger_buffer, 2, RUSTIC_OK, 42) ||
        !check_span("exact byte limit", at_limit, sizeof(at_limit), RUSTIC_OK, 1) ||
        !check_span("oversized length", source, LIMIT + 1, RUSTIC_ERR_STEP_LIMIT_EXCEEDED, -123) ||
        !check_span("embedded NUL after valid prefix", with_nul, sizeof(with_nul), RUSTIC_ERR_INVALID_ARGUMENT, -123) ||
        !check_span("embedded NUL in lazy branch", skipped_nul, sizeof(skipped_nul) - 1, RUSTIC_ERR_INVALID_ARGUMENT, -123) ||
        !check_span("included string terminator", "42", sizeof("42"), RUSTIC_ERR_INVALID_ARGUMENT, -123) ||
        !check_span("empty span", source, 0, RUSTIC_ERR_EXPECTED_INTEGER, -123) ||
        !check_span("NULL source", NULL, 0, RUSTIC_ERR_INVALID_ARGUMENT, -123) ||
        !check_span("truncated expression", larger_buffer, 3, RUSTIC_ERR_EXPECTED_INTEGER, -123)) {
        return 1;
    }
    if (rustic_eval_expression_n(source, sizeof(source), NULL) != RUSTIC_ERR_INVALID_ARGUMENT) {
        fputs("NULL output must be rejected\n", stderr);
        return 2;
    }
    if (rustic_eval_expression(larger_buffer, &out) != RUSTIC_ERR_EXPECTED_INTEGER || out != -123) {
        fputs("the string API must still evaluate up to its terminator\n", stderr);
        return 3;
    }
    if (!check_span("composed program after failures", program, sizeof(program) - 1, RUSTIC_OK, 42)) {
        return 4;
    }
    puts("C API source span: ok");
    return 0;
}
