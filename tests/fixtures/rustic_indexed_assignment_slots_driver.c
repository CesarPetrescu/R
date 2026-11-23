#include "rustic.h"

#include <stdio.h>

static int check(const char *label, const char *body, size_t slots,
                 RusticStatus expected_status, long expected_output) {
    char source[2048];
    size_t length = 0;
    size_t i;
    int written;
    long output = -123;
    RusticStatus status;

    for (i = 0; i < slots; i++) {
        written = snprintf(source + length, sizeof(source) - length,
                           "let a%zu=[%zu,5];", i, i);
        if (written < 0 || (size_t)written >= sizeof(source) - length) {
            return 0;
        }
        length += (size_t)written;
    }
    written = snprintf(source + length, sizeof(source) - length, "%s", body);
    if (written < 0 || (size_t)written >= sizeof(source) - length) {
        return 0;
    }
    status = rustic_eval_expression(source, &output);
    if (status != expected_status || output != expected_output) {
        fprintf(stderr, "%s: got %s, output %ld; expected %s, output %ld\n",
                label, rustic_status_message(status), output,
                rustic_status_message(expected_status), expected_output);
        return 0;
    }
    return 1;
}

int main(void) {
    int ok = 1;
    ok &= check("replace at capacity", "a0[0]=42; a0[0]+a63[0]", 64, RUSTIC_OK, 105);
    ok &= check("alias with one free slot", "let alias=a0; a0[0]=42; a0[0]+alias[0]", 63, RUSTIC_OK, 42);
    ok &= check("alias at capacity", "let alias=a0; a0[0]=42", 64, RUSTIC_ERR_TOO_MANY_BINDINGS, -123);
    ok &= check("enclosing call holds the old array", "fn pick(a,b){a[0]+b}; pick(a0,{a0[0]=42; 0})",
                64, RUSTIC_ERR_TOO_MANY_BINDINGS, -123);
    ok &= check("enclosing literal stays live", "[{a0[0]=42; a0[0]},7][1]+a0[0]", 63, RUSTIC_OK, 49);
    ok &= check("RHS rebinding preserves original elements", "a0[1]={a0=a63; 42}; a0[0]+a0[1]+a63[0]",
                64, RUSTIC_OK, 105);
    ok &= check("outer assignment holds the old array", "a0[1]={a0[0]=90; 42}",
                64, RUSTIC_ERR_TOO_MANY_BINDINGS, -123);
    ok &= check("nested assignment with one free slot", "a0[1]={a0[0]=90; 42}; a0[0]+a0[1]",
                63, RUSTIC_OK, 42);
    ok &= check("repeat update at capacity", "let n=0; while n<8 {a0[0]=n; n=n+1;}; a0[0]+a63[0]",
                64, RUSTIC_OK, 70);
    ok &= check("assignment still yields the assigned integer", "a63[0]=42", 64, RUSTIC_OK, 42);
    ok &= check("RHS errors before bounds or capacity", "let alias=a0; a0[2]=1/0",
                64, RUSTIC_ERR_DIVISION_BY_ZERO, -123);
    ok &= check("bounds error before capacity", "let alias=a0; a0[2]=42",
                64, RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS, -123);
    ok &= check("fresh call after failure", "6*7", 0, RUSTIC_OK, 42);
    return ok ? 0 : 1;
}
