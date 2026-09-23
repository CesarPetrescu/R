#include "rustic.h"

#include <stdio.h>
#include <string.h>

int main(void) {
    long out = 123;

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
    if (rustic_eval_expression(NULL, &out) != RUSTIC_ERR_EXPECTED_INTEGER || out != 20) {
        return 4;
    }
    if (rustic_eval_expression("1", NULL) != RUSTIC_ERR_EXPECTED_INTEGER) {
        return 5;
    }
    puts("C API success, overflow, output preservation and NULL diagnostics: ok");
    return 0;
}
