#include "rustic.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

static int check(const char *source, RusticStatus expected, long expected_value) {
    long output = 12345;
    RusticStatus status = rustic_eval_expression(source, &output);
    if (status != expected || output != expected_value) {
        fprintf(stderr, "left shift failed: %s (%s, %ld)\n",
                source, rustic_status_message(status), output);
        return 0;
    }
    return 1;
}

int main(void) {
    char source[128];
    long top_bit = LONG_MAX / 2 + 1;
    unsigned int count = (unsigned int)(sizeof(long) * CHAR_BIT - 2);
    if (!check("let read = 1 << 0; let write = 1 << 2; read | write", RUSTIC_OK, 5)) return 1;
    if (!check("0 && 1 << (1 / 0)", RUSTIC_OK, 0)) return 2;
    if (!check("0 && 1 <<", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 3;
    if (!check("1 << [1]", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 4;
    if (!check("-1 << 1", RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 5;
    if (!check("1 << -1", RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 6;
    if (!check("1 << 1 / 0", RUSTIC_ERR_DIVISION_BY_ZERO, 12345)) return 7;
    snprintf(source, sizeof(source), "1 << %u", count);
    if (!check(source, RUSTIC_OK, top_bit)) return 8;
    snprintf(source, sizeof(source), "1 << %u", count + 1);
    if (!check(source, RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 9;
    snprintf(source, sizeof(source), "2 << %u", count);
    if (!check(source, RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 10;
    snprintf(source, sizeof(source), "%ld << 1", LONG_MAX);
    if (!check(source, RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 11;
    snprintf(source, sizeof(source), "%ld << 0", LONG_MAX);
    if (!check(source, RUSTIC_OK, LONG_MAX)) return 12;
    if (!check("4 << 1", RUSTIC_OK, 8)) return 13;
    if (strcmp(rustic_status_message(RUSTIC_ERR_INTEGER_OVERFLOW), "integer overflow") != 0) return 14;
    return 0;
}
