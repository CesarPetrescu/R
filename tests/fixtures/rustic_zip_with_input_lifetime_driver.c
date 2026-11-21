#include "rustic.h"

#include <stdio.h>
#include <string.h>

static int check_zip(size_t bound_count, const char *program,
                     RusticStatus expected_status, long expected_output) {
    char source[2048];
    size_t used = 0;
    size_t i;
    long output = -123;
    RusticStatus status;

    for (i = 0; i < bound_count; i++) {
        int written = snprintf(source + used, sizeof(source) - used,
                               "let a%zu=[%zu]; ", i, i);
        if (written < 0 || (size_t)written >= sizeof(source) - used) {
            return 0;
        }
        used += (size_t)written;
    }
    if (strlen(program) >= sizeof(source) - used) {
        return 0;
    }
    strcpy(source + used, program);

    status = rustic_eval_expression(source, &output);
    if (status != expected_status || output != expected_output) {
        fprintf(stderr, "%zu bound arrays, %s: got %s (%ld), expected %s (%ld)\n",
                bound_count, program, rustic_status_message(status), output,
                rustic_status_message(expected_status), expected_output);
        return 0;
    }
    return 1;
}

int main(void) {
    int ok = 1;

    /* Either temporary input can relinquish the last slot to the callback. */
    ok &= check_zip(63, "fn pair(x,y){x+y+len([x])}; sum(zip_with(a0,[4],pair))",
                    RUSTIC_OK, 5);
    ok &= check_zip(63, "fn pair(x,y){x+y+len([x])}; sum(zip_with([4],a0,pair))",
                    RUSTIC_OK, 5);
    /* Both snapshots are needed, but neither input slot is; stop at the shorter side. */
    ok &= check_zip(62, "fn pair(x,y){x*10+y+len([x])+len([y])}; "
                        "sum(zip_with([1,2],[3,4,5],pair)) + a61[0]",
                    RUSTIC_OK, 102);
    /* Keep the earlier argument and the partially built literal live. */
    ok &= check_zip(62, "fn pair(x,y){x+y+len([x])}; "
                        "sum(concat([50],zip_with(a1,[4],pair)))",
                    RUSTIC_OK, 56);
    ok &= check_zip(62, "fn pair(x,y){x+y+len([x])}; "
                        "sum([7,zip_with(a1,[4],pair)[0]])",
                    RUSTIC_OK, 13);
    /* The callback may update a bound source without changing later pairs. */
    ok &= check_zip(63, "a0=push(a0,2); fn pair(x,y){a0=[99]; x+y}; "
                        "sum(zip_with(a0,[4,8],pair)) + a0[0]",
                    RUSTIC_OK, 113);

    ok &= check_zip(64, "fn pair(x,y){x+y+len([x])}; sum(zip_with(a0,a1,pair))",
                    RUSTIC_ERR_TOO_MANY_BINDINGS, -123);
    ok &= check_zip(64, "fn pair(x,y){x+y}; sum(zip_with(a0,a1,pair))",
                    RUSTIC_ERR_TOO_MANY_BINDINGS, -123);
    ok &= check_zip(63, "fn pair(x,y){x/(y-y)}; sum(zip_with(a0,[4],pair))",
                    RUSTIC_ERR_DIVISION_BY_ZERO, -123);
    ok &= check_zip(63, "fn pair(x,y){[x+y]}; sum(zip_with(a0,[4],pair))",
                    RUSTIC_ERR_EXPECTED_INTEGER, -123);
    ok &= check_zip(63, "fn pair(x,y){x/(y-y)}; len(zip_with(a0,[],pair))",
                    RUSTIC_OK, 0);
    ok &= check_zip(0, "fn pair(x,y){x+y}; zip_with([3],[4],pair)[0]",
                    RUSTIC_OK, 7);
    return ok ? 0 : 1;
}
