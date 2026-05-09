#include "rustic.h"

#include <stdio.h>

int main(int argc, char **argv) {
    const char *source;
    long value = 0;
    RusticStatus status;

    if (argc != 2) {
        fprintf(stderr, "usage: rustic-expression-demo '<expression>'\n");
        return 2;
    }

    source = argv[1];
    status = rustic_eval_expression(source, &value);
    if (status != RUSTIC_OK) {
        fprintf(stderr, "%s: %s\n", rustic_status_message(status), source);
        return 2;
    }

    printf("%s => %ld\n", source, value);
    return 0;
}
