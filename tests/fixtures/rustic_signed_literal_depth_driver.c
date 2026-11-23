#include "rustic.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

/* 63 parens plus the literal occupy all 64 factor frames. */
enum { LAST_LITERAL_DEPTH = 63 };

static int check(const char *prefix, const char *operand, size_t depth,
                 const char *suffix, RusticStatus expected, long expected_result) {
    char source[2 * (LAST_LITERAL_DEPTH + 1) + sizeof(long) * CHAR_BIT + 80];
    size_t offset = strlen(prefix);
    long out = 123;
    RusticStatus status;
    int written;

    memcpy(source, prefix, offset);
    memset(source + offset, '(', depth);
    offset += depth;
    memcpy(source + offset, operand, strlen(operand));
    offset += strlen(operand);
    memset(source + offset, ')', depth);
    offset += depth;
    written = snprintf(source + offset, sizeof(source) - offset, "%s", suffix);
    if (written < 0 || (size_t)written >= sizeof(source) - offset) {
        return 0;
    }
    status = rustic_eval_expression(source, &out);
    if (status != expected || out != (expected == RUSTIC_OK ? expected_result : 123)) {
        fprintf(stderr, "%s: expected %s, got %s (output %ld)\n",
                source, rustic_status_message(expected), rustic_status_message(status), out);
        return 0;
    }
    return 1;
}

int main(void) {
    const char *tokens[] = {"-1", "-0xA", "-0b1_0", "-0o7"};
    const long values[] = {-1, -10, -2, -7};
    char too_negative[sizeof(long) * CHAR_BIT + 3];
    size_t i;

    for (i = 0; i < sizeof(tokens) / sizeof(tokens[0]); i++) {
        if (!check("", tokens[i], LAST_LITERAL_DEPTH, "", RUSTIC_OK, values[i]) ||
                !check("1 || ", tokens[i], LAST_LITERAL_DEPTH, "", RUSTIC_OK, 1) ||
                !check("0 && ", tokens[i], LAST_LITERAL_DEPTH + 1, "",
                       RUSTIC_ERR_STEP_LIMIT_EXCEEDED, 0)) {
            return 1;
        }
    }
    if (!check("0 && ", "- 1", LAST_LITERAL_DEPTH - 1, "", RUSTIC_OK, 0) ||
            !check("0 && ", "- 1", LAST_LITERAL_DEPTH, "", RUSTIC_ERR_STEP_LIMIT_EXCEEDED, 0) ||
            !check("0 && ", "--1", LAST_LITERAL_DEPTH, "", RUSTIC_ERR_STEP_LIMIT_EXCEEDED, 0) ||
            !check("1 || ", "-0x", LAST_LITERAL_DEPTH, "", RUSTIC_ERR_EXPECTED_INTEGER, 0) ||
            !check("1 || ", "-0b2", LAST_LITERAL_DEPTH, "", RUSTIC_ERR_EXPECTED_INTEGER, 0) ||
            !check("1 || ", "-0o8", LAST_LITERAL_DEPTH, "", RUSTIC_ERR_EXPECTED_INTEGER, 0) ||
            !check("0 && ", "-1[0]", LAST_LITERAL_DEPTH, "", RUSTIC_ERR_STEP_LIMIT_EXCEEDED, 0)) {
        return 2;
    }
    if (snprintf(too_negative, sizeof(too_negative), "-%lu", (unsigned long)LONG_MAX + 2UL) < 0 ||
            !check("", too_negative, LAST_LITERAL_DEPTH, "", RUSTIC_ERR_INTEGER_OVERFLOW, 0) ||
            !check("0 && ", too_negative, LAST_LITERAL_DEPTH, "", RUSTIC_OK, 0)) {
        return 3;
    }
    if (!check("match 1 {1 => 7, _ => ", "-0o7", LAST_LITERAL_DEPTH - 1, "}", RUSTIC_OK, 7) ||
            !check("1 || ", "-0xA", LAST_LITERAL_DEPTH - 1, "[unknown]", RUSTIC_OK, 1) ||
            !check("1 || ", "-0xA", LAST_LITERAL_DEPTH - 1, "[0", RUSTIC_ERR_EXPECTED_CLOSING_BRACKET, 0) ||
            !check("", "2 + 3", 0, "", RUSTIC_OK, 5)) {
        return 4;
    }
    return 0;
}
