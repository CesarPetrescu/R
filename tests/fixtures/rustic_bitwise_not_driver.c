#include "rustic.h"

#include <stdio.h>
#include <string.h>

static int check(const char *source, RusticStatus expected, long value) {
    long output = 12345;
    RusticStatus status = rustic_eval_expression(source, &output);
    if (status != expected || output != value) {
        fprintf(stderr, "bitwise NOT contract failed: %s (%s, %ld)\n",
                source, rustic_status_message(status), output);
        return 0;
    }
    return 1;
}

int main(void) {
    if (!check("let flags = 0b1111; flags & ~0b0010", RUSTIC_OK, 13)) return 1;
    if (!check("~[1]", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 2;
    if (!check("0 && ~", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 3;
    if (!check("~(1 / 0)", RUSTIC_ERR_DIVISION_BY_ZERO, 12345)) return 4;
    if (!check("1 || ~[1]", RUSTIC_OK, 1)) return 5;
    if (!check("0b1111 & ~(0b0010 | 0b0100)", RUSTIC_OK, 9)) return 6;
    if (strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_INTEGER), "expected integer") != 0) return 7;
    return 0;
}
