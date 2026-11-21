#include "rustic.h"

#include <stdio.h>
#include <string.h>

static int check(unsigned int live_arrays, const char *body,
                 RusticStatus expected_status, long expected_output) {
    char source[2048];
    size_t used = 0;
    unsigned int i;
    long output = -123;
    RusticStatus status;

    for (i = 0; i < live_arrays; i++) {
        int written = snprintf(source + used, sizeof(source) - used,
                               "let a%u=[%u]; ", i, i);
        if (written < 0 || (size_t)written >= sizeof(source) - used) {
            return 0;
        }
        used += (size_t)written;
    }
    if (strlen(body) >= sizeof(source) - used) {
        return 0;
    }
    strcpy(source + used, body);
    status = rustic_eval_expression(source, &output);
    if (status != expected_status || output != expected_output) {
        fprintf(stderr, "%u bound arrays, %s: got %s (%ld), expected %s (%ld)\n",
                live_arrays, body, rustic_status_message(status), output,
                rustic_status_message(expected_status), expected_output);
        return 0;
    }
    return 1;
}

int main(void) {
    /* After reading the input, both callbacks can reuse the remaining slot. */
    if (!check(63, "fn step(acc,x){acc+x+len([x])}; fold([4,8],0,step)",
               RUSTIC_OK, 14)) return 1;
    /* An enclosing argument and the outer literal each count as live roots. */
    if (!check(62, "fn step(acc,x){acc+x+len([x])}; fn add(xs,n){xs[0]+n}; "
                   "add([50],fold([4,8],0,step)) + a61[0]",
               RUSTIC_OK, 125)) return 2;
    if (!check(62, "fn step(acc,x){acc+x+len([x])}; [fold([4,8],0,step)][0]",
               RUSTIC_OK, 14)) return 3;
    if (!check(63, "fn step(acc,x){acc+x+len([x])}; let i=0; let total=0; "
                   "while i<65 { total=total+fold([1],0,step); i=i+1; }; total",
               RUSTIC_OK, 130)) return 4;
    /* All 64 slots really are in use when the fold input is still bound. */
    if (!check(64, "fn step(acc,x){acc+x+len([x])}; fold(a0,0,step)",
               RUSTIC_ERR_TOO_MANY_BINDINGS, -123)) return 5;
    if (!check(63, "fn bad(acc,x){[x]}; fold([4],0,bad)",
               RUSTIC_ERR_EXPECTED_INTEGER, -123)) return 6;
    if (!check(0, "fn bad(acc,x){1/0}; fold([],7,bad)",
               RUSTIC_OK, 7)) return 7;
    return 0;
}
