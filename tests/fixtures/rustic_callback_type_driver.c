#include "rustic.h"

#include <stddef.h>
#include <string.h>

int main(void) {
    static const char *nonfunctions[] = {
        "map([1], 7)", "filter([], [1])", "partition_count([1], 7)",
        "map_indexed([1], 7)", "filter_indexed([1], [7])",
        "zip_with([1], [2], 7)", "fold([1], 0, [7])",
        "weighted_score([1], 7)"
    };
    long value = 81;
    size_t index;

    for (index = 0; index < sizeof(nonfunctions) / sizeof(nonfunctions[0]); index++) {
        if (rustic_eval_expression(nonfunctions[index], &value) != RUSTIC_ERR_EXPECTED_FUNCTION || value != 81) {
            return 1;
        }
    }
    if (strcmp(rustic_status_message(RUSTIC_ERR_EXPECTED_FUNCTION), "expected function") != 0) {
        return 2;
    }
    if (rustic_eval_expression("let f={fn hidden(x){x};hidden}; map([1],f)", &value) != RUSTIC_ERR_UNDEFINED_IDENTIFIER || value != 81) {
        return 3;
    }
    if (rustic_eval_expression("map(7, 7)", &value) != RUSTIC_ERR_EXPECTED_ARRAY || value != 81) {
        return 4;
    }
    if (rustic_eval_expression("fn inc(x){x+1}; sum(map([1,2],inc))", &value) != RUSTIC_OK || value != 5) {
        return 5;
    }
    return 0;
}
