#include "rustic.h"

#include <stdio.h>
#include <string.h>

static int expect_with_live_arrays(size_t count, const char *expression,
                                   RusticStatus expected_status, long expected_result) {
    char source[2048];
    size_t used = 0;
    size_t index;
    long result = -99;
    RusticStatus status;
    for (index = 0; index < count; index++) {
        int length = snprintf(source + used, sizeof(source) - used, "let a%zu=[];", index);
        if (length < 0 || (size_t)length >= sizeof(source) - used) {
            return 0;
        }
        used += (size_t)length;
    }
    if (strlen(expression) >= sizeof(source) - used) {
        return 0;
    }
    strcpy(source + used, expression);
    status = rustic_eval_expression(source, &result);
    if (status != expected_status || result != expected_result) {
        fprintf(stderr, "%zu live arrays, %s: got %s / %ld; expected %s / %ld\n",
                count, expression, rustic_status_message(status), result,
                rustic_status_message(expected_status), expected_result);
        return 0;
    }
    return 1;
}

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
    if (!expect_with_live_arrays(63, "[1] == [1]", RUSTIC_OK, 1)) {
        return 8;
    }
    if (!expect_with_live_arrays(63, "[1] == [1] && [2] != [3]", RUSTIC_OK, 1)) {
        return 9;
    }
    if (!expect_with_live_arrays(63, "fn make(){[4]}; make() == { a0=7; [4] } && a0 == 7",
                                 RUSTIC_OK, 1)) {
        return 10;
    }
    if (!expect_with_live_arrays(62, "fn pick(xs,flag){xs[0]+flag}; pick([9], [1] != [2])",
                                 RUSTIC_OK, 10)) {
        return 11;
    }
    if (!expect_with_live_arrays(62, "sum([[1] != [2]])", RUSTIC_OK, 1)) {
        return 12;
    }
    if (!expect_with_live_arrays(64, "a63 == a0 && len(a63) == 0", RUSTIC_OK, 1)) {
        return 13;
    }
    if (!expect_with_live_arrays(64, "a63 == [1]", RUSTIC_ERR_TOO_MANY_BINDINGS, -99)) {
        return 14;
    }
    if (!expect_with_live_arrays(63, "sum([[1] != [2]])", RUSTIC_ERR_TOO_MANY_BINDINGS, -99)) {
        return 15;
    }
    if (!expect_with_live_arrays(63, "fn pick(xs,flag){xs[0]+flag}; pick([9], [1] != [2])",
                                 RUSTIC_ERR_TOO_MANY_BINDINGS, -99)) {
        return 16;
    }
    if (!expect_with_live_arrays(63, "[1] != { a0=7; 1 / 0 }", RUSTIC_ERR_DIVISION_BY_ZERO, -99)) {
        return 17;
    }
    if (!expect_with_live_arrays(64, "0 && ([1] == [1])", RUSTIC_OK, 0)) {
        return 18;
    }
    /* A false condition can read a previous body result after replacing its binding. */
    if (!expect_with_live_arrays(0,
            "let x=[3]; let i=0; sum({while i==0 || {let old=x; x=0; old} == [] {i=1; x};})",
            RUSTIC_OK, 3)) {
        return 19;
    }
    if (!expect_with_live_arrays(0,
            "let zero=[]; let x=[3]; let i=0; "
            "sum({while i==0 || zero == {let old=x; x=0; old} || [1]==[2] {i=1; x};})",
            RUSTIC_OK, 3)) {
        return 20;
    }
    if (rustic_eval_expression("6 * 7", &result) != RUSTIC_OK || result != 42) {
        return 21;
    }
    return 0;
}
