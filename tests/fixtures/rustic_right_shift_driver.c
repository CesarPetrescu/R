#include "rustic.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

static int check(const char *source, RusticStatus expected, long expected_value) {
    long output = 12345;
    RusticStatus status = rustic_eval_expression(source, &output);
    if (status != expected || output != expected_value) {
        fprintf(stderr, "right shift failed: %s (%s, %ld)\n",
                source, rustic_status_message(status), output);
        return 0;
    }
    return 1;
}

int main(void) {
    char source[128];
    unsigned int max_count = (unsigned int)(sizeof(long) * CHAR_BIT - 2);
    long high_bit = LONG_MAX / 2 + 1;
    if (!check("let f = (1 << 4) | (1 << 2); (f >> 2) & 1", RUSTIC_OK, 1)) return 1;
    if (!check("0 && 8 >> (1 / 0)", RUSTIC_OK, 0)) return 2;
    if (!check("0 && 8 >>", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 3;
    if (!check("8 >> [1]", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 4;
    if (!check("-1 >> 1", RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 5;
    if (!check("8 >> -1", RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 6;
    if (!check("8 >> 1 / 0", RUSTIC_ERR_DIVISION_BY_ZERO, 12345)) return 7;
    snprintf(source, sizeof(source), "%ld >> %u", LONG_MAX, max_count);
    if (!check(source, RUSTIC_OK, 1)) return 8;
    snprintf(source, sizeof(source), "1 >> %u", max_count + 1);
    if (!check(source, RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 9;
    snprintf(source, sizeof(source), "%ld >> 0", LONG_MAX);
    if (!check(source, RUSTIC_OK, LONG_MAX)) return 10;
    snprintf(source, sizeof(source), "%ld >> %u", high_bit, max_count);
    if (!check(source, RUSTIC_OK, 1)) return 11;
    if (!check("4 >> 1", RUSTIC_OK, 2)) return 12;
    if (strcmp(rustic_status_message(RUSTIC_ERR_INTEGER_OVERFLOW), "integer overflow") != 0) return 13;
    return 0;
}
