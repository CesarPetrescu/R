#include "rustic.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

static int check(const char *source, RusticStatus expected_status, long expected_output) {
    long output = 12345;
    RusticStatus status = rustic_eval_expression(source, &output);
    if (status != expected_status || output != expected_output) {
        fprintf(stderr, "%s: got %s (%ld), expected %s (%ld)\n", source,
                rustic_status_message(status), output,
                rustic_status_message(expected_status), expected_output);
        return 0;
    }
    return 1;
}

int main(void) {
    char boundary[128];
    char source[2048] = "";
    char *tail = source;
    int i;

    if (!check("[1; 17][0]", RUSTIC_ERR_TOO_MANY_BINDINGS, 12345)) return 1;
    snprintf(boundary, sizeof(boundary), "[1; %ld][0]", LONG_MAX);
    if (!check(boundary, RUSTIC_ERR_TOO_MANY_BINDINGS, 12345)) return 2;
    if (!check("[1; 16][15]", RUSTIC_OK, 1)) return 3;
    if (!check("len([1; -1])", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 4;
    if (!check("1 || [1; 2,]", RUSTIC_ERR_EXPECTED_CLOSING_BRACKET, 12345)) return 5;
    if (!check("0 && [1; 0o8]", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 6;
    if (!check("while 1 { [1; {break;}]; 1/0; }; 42", RUSTIC_OK, 42)) return 7;
    if (!check("while 1 { [{fn f(){1}; f; break;}; 1/0]; }; 42", RUSTIC_OK, 42)) return 8;

    for (i = 0; i < 63; i++) {
        size_t remaining = sizeof(source) - (size_t)(tail - source);
        int written = snprintf(tail, remaining, "let a%d=[%d]; ", i, i);
        if (written < 0 || (size_t)written >= remaining) return 13;
        tail += written;
    }
    strcpy(tail, "let n=0; while n<4 { [1; {n=n+1; continue;}]; }; [a62[0]; 16][15]+n");
    if (!check(source, RUSTIC_OK, 66)) return 9;
    strcpy(tail, "[7; 2][1]+a62[0]");
    if (!check(source, RUSTIC_OK, 69)) return 10;
    strcpy(tail, "let full=[0]; len([7; 2])");
    if (!check(source, RUSTIC_ERR_TOO_MANY_BINDINGS, 12345)) return 11;
    if (!check("6 * 7", RUSTIC_OK, 42)) return 12;
    return 0;
}
