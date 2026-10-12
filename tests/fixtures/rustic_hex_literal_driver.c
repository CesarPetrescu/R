#include "rustic.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

static int check(const char *source, RusticStatus expected, long expected_value) {
    long output = 12345;
    RusticStatus status = rustic_eval_expression(source, &output);
    if (status != expected || output != expected_value) {
        fprintf(stderr, "hex contract failed: %s (%s, %ld)\n",
                source, rustic_status_message(status), output);
        return 0;
    }
    return 1;
}

int main(void) {
    char source[512];
    unsigned long beyond_positive = (unsigned long)LONG_MAX + 1UL;

    snprintf(source, sizeof(source), "0x%lX", (unsigned long)LONG_MAX);
    if (!check(source, RUSTIC_OK, LONG_MAX)) return 1;
    snprintf(source, sizeof(source), "-0x%lX", beyond_positive);
    if (!check(source, RUSTIC_OK, LONG_MIN)) return 2;
    snprintf(source, sizeof(source), "0x%lX", beyond_positive);
    if (!check(source, RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 3;
    snprintf(source, sizeof(source), "-0x%lX", beyond_positive + 1UL);
    if (!check(source, RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 4;
    snprintf(source, sizeof(source), "match 0 { 0 => 1, 0x%lX => 2 }", beyond_positive);
    if (!check(source, RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 5;
    snprintf(source, sizeof(source), "match -0x%lX { -0x%lX => 7, _ => 0 }",
             beyond_positive, beyond_positive);
    if (!check(source, RUSTIC_OK, 7)) return 6;
    if (!check("0 && 0x_1", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 7;
    if (!check("0 && 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", RUSTIC_OK, 0)) return 8;
    if (!check("let x = 0x2A; x", RUSTIC_OK, 42)) return 9;
    if (strcmp(rustic_status_message(RUSTIC_ERR_INTEGER_OVERFLOW), "integer overflow") != 0) return 10;
    return 0;
}
