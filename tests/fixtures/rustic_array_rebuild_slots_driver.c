#include "rustic.h"

#include <stdio.h>

static int check(size_t bound_count, const char *program, RusticStatus expected_status,
                 long expected_value) {
    char source[2048];
    size_t used = 0;
    size_t i;
    long output = -123;
    RusticStatus status;
    int written;

    for (i = 0; i < bound_count; i++) {
        written = snprintf(source + used, sizeof(source) - used, "let a%zu=[%zu]; ", i, i);
        if (written < 0 || (size_t)written >= sizeof(source) - used) {
            return 0;
        }
        used += (size_t)written;
    }
    written = snprintf(source + used, sizeof(source) - used, "%s", program);
    if (written < 0 || (size_t)written >= sizeof(source) - used) {
        return 0;
    }

    status = rustic_eval_expression(source, &output);
    if (status != expected_status || output != expected_value) {
        fprintf(stderr, "%zu bound arrays, %s: got %s (%ld), expected %s (%ld)\n",
                bound_count, program, rustic_status_message(status), output,
                rustic_status_message(expected_status), expected_value);
        return 0;
    }
    return 1;
}

int main(void) {
    int ok = 1;

    /* A temporary source can give its slot to the result, even successively. */
    ok &= check(63, "sum(push([], 7))", RUSTIC_OK, 7);
    ok &= check(63, "set([2], 0, 7)[0]", RUSTIC_OK, 7);
    ok &= check(63, "set(push([2], 3), 0, 7)[0] + a62[0]", RUSTIC_OK, 69);
    /* Enclosing roots remain live while the temporary source is replaced. */
    ok &= check(62, "fn combine(left,right){left[0]+right[0]}; combine([50], set([1],0,7))",
                RUSTIC_OK, 57);
    ok &= check(62, "sum([4, push([1],7)[1]])", RUSTIC_OK, 11);
    /* Bound sources and their aliases cannot be reclaimed. */
    ok &= check(63, "let alias=a1; set(a1,0,7)[0] + alias[0]", RUSTIC_OK, 8);
    ok &= check(64, "push(a1,7)[1]", RUSTIC_ERR_TOO_MANY_BINDINGS, -123);
    ok &= check(64, "set(a1,0,7)[0]", RUSTIC_ERR_TOO_MANY_BINDINGS, -123);
    /* Existing errors precede rebuilding, and each failed call preserves output. */
    ok &= check(63, "set([2],1,7)[0]", RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS, -123);
    ok &= check(63, "push(range(16),7)[0]", RUSTIC_ERR_TOO_MANY_BINDINGS, -123);
    ok &= check(64, "set(a1,0,a2)[0]", RUSTIC_ERR_EXPECTED_INTEGER, -123);
    ok &= check(63, "0 && push([],1 / 0)[0]", RUSTIC_OK, 0);
    ok &= check(0, "push([2],7)[1]", RUSTIC_OK, 7);
    return ok ? 0 : 1;
}
