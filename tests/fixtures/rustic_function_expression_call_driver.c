#include "rustic.h"
#include <string.h>

int main(void) {
    long output = 91;
    if (rustic_eval_expression("fn inc(x){x+1}; (inc)(2)", &output) != RUSTIC_OK || output != 3) return 1;
    if (rustic_eval_expression("fn inc(x){x+1}; (inc)()", &output) != RUSTIC_ERR_WRONG_ARGUMENT_COUNT || output != 3) return 2;
    if (rustic_eval_expression("let x=5; (x)()", &output) != RUSTIC_ERR_EXPECTED_FUNCTION || output != 3) return 3;
    if (rustic_eval_expression("fn inc(x){x+1}; 0 && (inc)(1 + *)", &output) != RUSTIC_ERR_EXPECTED_INTEGER || output != 3) return 4;
    if (rustic_eval_expression("fn inc(x){x+1}; (inc)(1/0)", &output) != RUSTIC_ERR_DIVISION_BY_ZERO || output != 3) return 5;
    if (rustic_eval_expression("fn f(){1}; let saved=0; {fn old(){2}; saved=old; 0}; fn fresh(){3}; (saved)()", &output) != RUSTIC_ERR_UNDEFINED_IDENTIFIER || output != 3) return 6;
    if (strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_FUNCTION), "expected function") != 0) return 7;
    if (rustic_eval_expression("fn inc(x){x+1}; fn pick(){inc}; pick()(8)", &output) != RUSTIC_OK || output != 9) return 8;
    return 0;
}
