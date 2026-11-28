#include "rustic.h"

#include <stdio.h>

static int check_range(unsigned int live_count, const char *expression,
                       RusticStatus expected_status, long expected_value) {
    char source[2048];
    size_t used = 0;
    unsigned int i;
    int written;
    RusticStatus status;
    const long sentinel = -12345;
    long output = sentinel;

    for (i = 0; i < live_count; i++) {
        written = snprintf(source + used, sizeof(source) - used, "let a%u=[%u];", i, i);
        if (written < 0 || (size_t)written >= sizeof(source) - used) {
            return 0;
        }
        used += (size_t)written;
    }
    written = snprintf(source + used, sizeof(source) - used, "%s", expression);
    if (written < 0 || (size_t)written >= sizeof(source) - used) {
        return 0;
    }

    status = rustic_eval_expression(source, &output);
    if (status != expected_status || output != (status == RUSTIC_OK ? expected_value : sentinel)) {
        fprintf(stderr, "%u bound arrays; %s: got %s (%ld), expected %s (%ld)\n",
                live_count, expression, rustic_status_message(status), output,
                rustic_status_message(expected_status),
                expected_status == RUSTIC_OK ? expected_value : sentinel);
        return 0;
    }
    return rustic_eval_expression("6 * 7", &output) == RUSTIC_OK && output == 42;
}

int main(void) {
    int ok = 1;

    /* The length's array is dead before range builds the result. */
    ok &= check_range(63, "sum(range(len([7,8,9])))+a62[0]", RUSTIC_OK, 65);
    ok &= check_range(63, "len(range(len([])))", RUSTIC_OK, 0);

    /* A newer binding may occupy the tail after the consumed temporary. */
    ok &= check_range(62, "let saved=0; len(range(len([{saved=[8];7}])))+saved[0]+a61[0]",
                      RUSTIC_OK, 70);

    /* Compaction must retain older roots, even when nothing binds them. */
    ok &= check_range(62, "fn pick(xs,k){xs[0]+k}; pick([9],len(range(len([7]))))",
                      RUSTIC_OK, 10);
    ok &= check_range(62, "sum([len(range(len([7])))])", RUSTIC_OK, 1);
    ok &= check_range(62, "sum({let i=0; while len(range(len([0])))-i {i=1;[3]};})+a61[0]",
                      RUSTIC_OK, 64);

    /* True exhaustion, the usual argument and index errors, and lazy calls. */
    ok &= check_range(64, "len(range(len(a0)))", RUSTIC_ERR_TOO_MANY_BINDINGS, 0);
    ok &= check_range(63, "sum([len(range(1))])", RUSTIC_ERR_TOO_MANY_BINDINGS, 0);
    ok &= check_range(63, "range(len([7]))[1]", RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS, 0);
    ok &= check_range(63, "len(range(len([7])-2))", RUSTIC_ERR_EXPECTED_INTEGER, 0);
    ok &= check_range(63, "len(range(len([7])+16))", RUSTIC_ERR_TOO_MANY_BINDINGS, 0);
    ok &= check_range(64, "0 && range(len([7]))", RUSTIC_OK, 0);
    ok &= check_range(64, "0 && range(len([,]))", RUSTIC_ERR_EXPECTED_INTEGER, 0);
    return ok ? 0 : 1;
}
