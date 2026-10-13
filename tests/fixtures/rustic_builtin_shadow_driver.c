#include "rustic.h"

#include <string.h>

int main(void) {
    long result = 81;

    if (rustic_eval_expression("fn sum(x) { x + 1 }; sum(2)", &result) != RUSTIC_OK || result != 3) {
        return 1;
    }
    if (rustic_eval_expression("let sum = 7; sum([1])", &result) != RUSTIC_ERR_EXPECTED_FUNCTION || result != 3) {
        return 2;
    }
    if (strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_FUNCTION), "expected function") != 0) {
        return 3;
    }
    if (rustic_eval_expression("fn len(x) { x + 1 }; len([1])", &result) != RUSTIC_ERR_EXPECTED_INTEGER || result != 3) {
        return 4;
    }
    if (rustic_eval_expression("{ fn sum(x) { x + 5 }; sum(2) }; sum([1, 2])", &result) != RUSTIC_OK || result != 3) {
        return 5;
    }
    if (rustic_eval_expression("let xs = [4]; len(xs)", &result) != RUSTIC_OK || result != 1) {
        return 6;
    }
    return 0;
}
