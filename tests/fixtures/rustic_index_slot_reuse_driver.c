#include "rustic.h"

#include <stdio.h>
#include <string.h>

static int check(size_t count, const char *expression, RusticStatus expected, long result) {
    char source[2048];
    size_t used = 0;
    size_t i;
    long output = -99;
    RusticStatus status;

    for (i = 0; i < count; i++) {
        int written = snprintf(source + used, sizeof(source) - used, "let a%zu=[];", i);
        if (written < 0 || (size_t)written >= sizeof(source) - used) {
            return 0;
        }
        used += (size_t)written;
    }
    if (strlen(expression) >= sizeof(source) - used) {
        return 0;
    }
    strcpy(source + used, expression);
    status = rustic_eval_expression(source, &output);
    if (status != expected || output != result) {
        fprintf(stderr, "%zu bound arrays, %s: got %s / %ld, expected %s / %ld\n",
                count, expression, rustic_status_message(status), output,
                rustic_status_message(expected), result);
        return 0;
    }
    return 1;
}

int main(void) {
    if (!check(63, "[1][0] + [2][0]", RUSTIC_OK, 3)) {
        return 1;
    }
    if (!check(62, "[[1][0], [2][0]][1]", RUSTIC_OK, 2)) {
        return 2;
    }
    if (!check(62, "fn f(xs,n){xs[0]+n}; f([9], [1][0] + [2][0])", RUSTIC_OK, 12)) {
        return 3;
    }
    if (!check(62, "[9][[1][0] - 1] + [2][0]", RUSTIC_OK, 11)) {
        return 4;
    }
    if (!check(62, "let kept=0; [4][{kept=[7]; 0}] + kept[0]", RUSTIC_OK, 11) ||
        !check(63, "let xs=[9]; xs[0] + xs[0]", RUSTIC_OK, 18)) {
        return 5;
    }
    /* Reading an older handle must not reclaim the previous loop result. */
    if (!check(0, "let x=[3]; let i=0; "
                  "sum({while i==0 || {let old=x; x=0; old}[0] == 0 {i=1; x};})",
               RUSTIC_OK, 3)) {
        return 6;
    }
    if (!check(63, "[[1][0]][0]", RUSTIC_ERR_TOO_MANY_BINDINGS, -99) ||
        !check(64, "[1][0]", RUSTIC_ERR_TOO_MANY_BINDINGS, -99) ||
        !check(64, "a63[0]", RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS, -99)) {
        return 7;
    }
    if (!check(63, "[1][1 / 0] + [2][0]", RUSTIC_ERR_DIVISION_BY_ZERO, -99) ||
        !check(63, "[1][0][0]", RUSTIC_ERR_EXPECTED_ARRAY, -99) ||
        !check(63, "[1][0][[0][0]]", RUSTIC_ERR_EXPECTED_ARRAY, -99)) {
        return 8;
    }
    if (!check(64, "0 && ([1][0] + [2][0])", RUSTIC_OK, 0) ||
        !check(0, "6 * 7", RUSTIC_OK, 42)) {
        return 9;
    }
    return 0;
}
