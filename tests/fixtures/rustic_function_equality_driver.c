#include "rustic.h"

#include <string.h>

int main(void) {
    long result = 83;
    if (rustic_eval_expression("fn f(){1}; let a=f; f == a", &result) != RUSTIC_OK || result != 1) {
        return 1;
    }
    if (rustic_eval_expression("fn f(){1}; fn g(){1}; f != g", &result) != RUSTIC_OK || result != 1) {
        return 2;
    }
    if (rustic_eval_expression("fn f(){1}; f == 1", &result) != RUSTIC_ERR_EXPECTED_FUNCTION || result != 1) {
        return 3;
    }
    if (strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_FUNCTION), "expected function") != 0) {
        return 4;
    }
    if (rustic_eval_expression("fn f(){1}; 1 == f", &result) != RUSTIC_ERR_EXPECTED_INTEGER || result != 1) {
        return 5;
    }
    if (rustic_eval_expression("let saved=0; {fn old(){1}; saved=old; 0}; fn new(){2}; saved == new", &result) != RUSTIC_ERR_UNDEFINED_IDENTIFIER || result != 1) {
        return 6;
    }
    if (rustic_eval_expression("fn f(){1}; let saved=0; {fn old(){1}; saved=old; 0}; f == saved", &result) != RUSTIC_ERR_UNDEFINED_IDENTIFIER || result != 1) {
        return 7;
    }
    if (rustic_eval_expression("fn f(){1}; f == { 1 / 0 }", &result) != RUSTIC_ERR_DIVISION_BY_ZERO || result != 1) {
        return 8;
    }
    if (rustic_eval_expression("fn f(){1}; f == f", &result) != RUSTIC_OK || result != 1) {
        return 9;
    }
    return 0;
}
