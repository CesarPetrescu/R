#include "rustic.h"

#include <string.h>

int main(void) {
    long result = 83;
    if (rustic_eval_expression("push([1], 2) == [1, 2]", &result) != RUSTIC_OK || result != 1) {
        return 1;
    }
    if (rustic_eval_expression("[1, 2] != [1, 2]", &result) != RUSTIC_OK || result != 0) {
        return 2;
    }
    if (rustic_eval_expression("[1] == 1", &result) != RUSTIC_ERR_EXPECTED_ARRAY || result != 0) {
        return 3;
    }
    if (strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_ARRAY), "expected array") != 0) {
        return 4;
    }
    if (rustic_eval_expression("1 == [1]", &result) != RUSTIC_ERR_EXPECTED_INTEGER || result != 0) {
        return 5;
    }
    if (rustic_eval_expression("[1] == [1] == [1]", &result) != RUSTIC_ERR_EXPECTED_OPERATOR || result != 0) {
        return 6;
    }
    if (rustic_eval_expression("let xs = [2]; xs == [2]", &result) != RUSTIC_OK || result != 1) {
        return 7;
    }
    return 0;
}
