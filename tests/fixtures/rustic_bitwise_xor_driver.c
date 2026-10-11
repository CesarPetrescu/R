#include "rustic.h"

#include <stdio.h>
#include <string.h>

static int check(const char *source, RusticStatus expected, long expected_value) {
    long output = 12345;
    RusticStatus status = rustic_eval_expression(source, &output);
    if (status != expected || output != expected_value) {
        fprintf(stderr, "bitwise XOR contract failed: %s (%s, %ld)\n",
                source, rustic_status_message(status), output);
        return 0;
    }
    return 1;
}

int main(void) {
    if (!check("let flags = 0b0111; flags ^ 0b0010", RUSTIC_OK, 5)) return 1;
    if (!check("1 ^", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 2;
    if (!check("0 && 1 ^", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 3;
    if (!check("1 ^ [1]", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 4;
    if (!check("0 && 1 / 0 ^ 2", RUSTIC_OK, 0)) return 5;
    if (!check("1 || 1 / 0 ^ 2", RUSTIC_OK, 1)) return 6;
    if (strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_INTEGER), "expected integer") != 0) return 7;
    if (!check("0b0101 ^ 0b0011", RUSTIC_OK, 6)) return 8;
    return 0;
}
