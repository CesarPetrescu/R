#include "rustic.h"

#include <string.h>

int main(void) {
    long out = 93;
    if (rustic_eval_expression("let x = 3;", &out) != RUSTIC_ERR_EXPECTED_INTEGER || out != 93) {
        return 1;
    }
    if (rustic_eval_expression("fn f() { 7 };", &out) != RUSTIC_ERR_EXPECTED_INTEGER || out != 93) {
        return 2;
    }
    if (strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_INTEGER), "expected integer") != 0) {
        return 3;
    }
    if (rustic_eval_expression("let x = 3; x", &out) != RUSTIC_OK || out != 3) {
        return 4;
    }
    if (rustic_eval_expression("1; let x = 3;", &out) != RUSTIC_OK || out != 1) {
        return 5;
    }
    return 0;
}
