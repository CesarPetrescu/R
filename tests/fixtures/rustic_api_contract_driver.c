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
    if (rustic_eval_expression(NULL, &out) != RUSTIC_ERR_EXPECTED_INTEGER || out != 20) {
        return 4;
    }
    if (rustic_eval_expression("1", NULL) != RUSTIC_ERR_EXPECTED_INTEGER) {
        return 5;
    }
    puts("C API success, overflow, output preservation and NULL diagnostics: ok");
    return 0;
}
