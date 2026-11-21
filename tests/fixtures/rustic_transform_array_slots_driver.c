#include "rustic.h"

#include <stdio.h>
#include <string.h>

static int check(unsigned int live_arrays, const char *program,
                 RusticStatus expected_status, long expected_value) {
    char source[2048];
    size_t used = 0;
    unsigned int i;
    long output = -123;
    RusticStatus status;

    for (i = 0; i < live_arrays; i++) {
        int count = snprintf(source + used, sizeof(source) - used,
                             "let a%u=[%u]; ", i, i);
        if (count < 0 || (size_t)count >= sizeof(source) - used) {
            return 0;
        }
        used += (size_t)count;
    }
    if (strlen(program) >= sizeof(source) - used) {
        return 0;
    }
    strcpy(source + used, program);
    status = rustic_eval_expression(source, &output);
    if (status != expected_status || output != expected_value) {
        fprintf(stderr, "%u live arrays, %s: got %s (%ld), expected %s (%ld)\n",
                live_arrays, program, rustic_status_message(status), output,
                rustic_status_message(expected_status), expected_value);
        return 0;
    }
    return 1;
}

int main(void) {
    /* Keep the enclosing concat argument live while the callback allocates. */
    if (!check(62, "fn keep(i,x){i == len([x])}; "
                   "sum(concat([50],filter_indexed([4,8],keep))) + a61[0]",
               RUSTIC_OK, 119)) return 1;
    if (!check(63, "fn keep(x){len([x]) && x == 8}; sum(filter([4,8],keep))",
               RUSTIC_OK, 8)) return 2;
    if (!check(63, "fn add(i,x){i*10+x+len([x])}; sum(map_indexed([4,8],add))",
               RUSTIC_OK, 24)) return 3;
    /* Do not reclaim the outer array under construction. */
    if (!check(62, "fn add(x){x+len([x])}; [sum(map([4,8],add))][0]",
               RUSTIC_OK, 14)) return 4;
    if (!check(63, "let i=0; let total=0; fn add(x){x+len([x])}; "
                   "while i<65 { total=total+sum(map([4,8],add)); i=i+1; }; total",
               RUSTIC_OK, 910)) return 5;
    /* A bound input must not be discarded even if all slots are occupied. */
    if (!check(64, "fn next(x){x+1}; sum(map(a0,next))",
               RUSTIC_ERR_TOO_MANY_BINDINGS, -123)) return 6;
    if (!check(64, "fn length(x){len([x])}; sum(map(a0,length))",
               RUSTIC_ERR_TOO_MANY_BINDINGS, -123)) return 7;
    if (!check(63, "fn invalid(x){x/0}; sum(map([4],invalid))",
               RUSTIC_ERR_DIVISION_BY_ZERO, -123)) return 8;
    if (!check(0, "fn inc(x){x+1}; sum(map([6],inc))", RUSTIC_OK, 7)) return 9;
    return 0;
}
