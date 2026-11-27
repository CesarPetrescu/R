#include "rustic.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

static int check(const char *suffix, int live_arrays, RusticStatus expected, long value) {
    char source[2048];
    size_t used = 0;
    int i;
    long output = -12345;
    RusticStatus status;

    for (i = 0; i < live_arrays; i++) {
        int written = snprintf(source + used, sizeof(source) - used, "let a%d=[%d];", i, i);
        if (written < 0 || (size_t)written >= sizeof(source) - used) {
            return 0;
        }
        used += (size_t)written;
    }
    if (strlen(suffix) >= sizeof(source) - used) {
        return 0;
    }
    strcpy(source + used, suffix);
    status = rustic_eval_expression(source, &output);
    if (status != expected || output != value) {
        fprintf(stderr, "%d arrays, %s: got %s (%ld), expected %s (%ld)\n",
                live_arrays, suffix, rustic_status_message(status), output,
                rustic_status_message(expected), value);
        return 0;
    }
    return 1;
}

int main(void) {
    char overflow[128];
    static const struct {
        const char *suffix;
        long expected;
    } transforms[] = {
        {"sum(reverse([3,7]))+a62[0]", 72},
        {"take([3,7],1)[0]", 3},
        {"drop([3,7],1)[0]", 7},
        {"sort([7,3])[0]", 3},
        {"len(dedup([7,3,7]))", 2},
        {"window_sum([3,7,9],2)[1]", 16},
        {"moving_average_sum([3,7,9],2)[1]", 8},
        {"chunk_sum([3,7,9],2)[0]", 10},
        {"rotate([3,7,9],1)[0]", 7},
        {"rotate_right([3,7,9],1)[0]", 9},
        {"prefix_sum([3,7])[1]", 10},
        {"adjacent_diff([3,7])[1]", 4},
        {"reverse(sort([3,7]))[0]", 7},
        {"len(reverse([]))", 0},
    };
    size_t i;

    for (i = 0; i < sizeof(transforms) / sizeof(transforms[0]); i++) {
        if (!check(transforms[i].suffix, 63, RUSTIC_OK, transforms[i].expected)) return 1;
    }
    if (!check("fn total(x,y){sum(x)+sum(y)}; total([8,9],reverse([3,7]))+a61[0]",
               62, RUSTIC_OK, 88)) return 2;
    if (!check("[sum(reverse([3,7])),a61[0]][0]", 62, RUSTIC_OK, 10)) return 3;
    if (!check("let a=[4,5]; let i=0; "
               "sum({while i==0 || len(reverse({let old=a; a=0; old}))==0 {i=1; a};})",
               0, RUSTIC_OK, 9)) return 4;
    if (!check("let alias=a62; reverse(a62)[0]+alias[0]+a62[0]", 63, RUSTIC_OK, 186)) return 5;
    if (!check("reverse(a0)[0]", 64, RUSTIC_ERR_TOO_MANY_BINDINGS, -12345)) return 6;
    if (!check("[sum(reverse([3,7]))][0]", 63, RUSTIC_ERR_TOO_MANY_BINDINGS, -12345)) return 7;
    if (!check("0 && reverse([3,7])[0]", 64, RUSTIC_OK, 0)) return 8;
    if (!check("1 || reverse([3,7])[", 64, RUSTIC_ERR_EXPECTED_INTEGER, -12345)) return 9;
    if (!check("len(take([3,7],-1))", 63, RUSTIC_ERR_EXPECTED_INTEGER, -12345)) return 10;
    if (!check("len(reverse(0))", 64, RUSTIC_ERR_EXPECTED_ARRAY, -12345)) return 11;
    snprintf(overflow, sizeof(overflow), "prefix_sum([%ld,1])[0]", LONG_MAX);
    if (!check(overflow, 63, RUSTIC_ERR_INTEGER_OVERFLOW, -12345)) return 12;
    if (!check("reverse([5,7])[0] * 6", 0, RUSTIC_OK, 42)) return 13;
    return 0;
}
