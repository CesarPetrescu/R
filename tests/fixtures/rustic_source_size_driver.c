#include "rustic.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    enum { LIMIT = 65536 };
    char *source = malloc(LIMIT + 2);
    long output = 123;
    if (source == NULL) {
        return 1;
    }

    source[0] = '1';
    memset(source + 1, ' ', LIMIT - 1);
    source[LIMIT] = '\0';
    if (rustic_eval_expression(source, &output) != RUSTIC_OK || output != 1) {
        free(source);
        return 2;
    }

    source[LIMIT] = ' ';
    source[LIMIT + 1] = '\0';
    output = 123;
    if (rustic_eval_expression(source, &output) != RUSTIC_ERR_STEP_LIMIT_EXCEEDED ||
        output != 123) {
        free(source);
        return 3;
    }
    if (strcmp(rustic_status_message(RUSTIC_ERR_STEP_LIMIT_EXCEEDED),
               "step limit exceeded") != 0) {
        free(source);
        return 4;
    }

    memset(source, ' ', LIMIT + 1);
    source[LIMIT + 1] = '\0';
    if (rustic_eval_expression(source, &output) != RUSTIC_ERR_STEP_LIMIT_EXCEEDED ||
        output != 123) {
        free(source);
        return 5;
    }
    free(source);

    if (rustic_eval_expression("let x = 2; x + 3", &output) != RUSTIC_OK || output != 5) {
        return 6;
    }
    puts("C API bounded source and recovery: ok");
    return 0;
}
