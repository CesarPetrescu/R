#include "rustic.h"

#include <stdio.h>
#include <string.h>

#define DECLARE_LAST "fn last(a,b,c,d,e,f,g,h){h}; "
#define SCALAR_CALL "last(1,2,3,4,5,6,7,"
#define NEW_ARRAY_CALL "last([],[],[],[],[],[],[],"
#define ALIAS_CALL "last(xs,xs,xs,xs,xs,xs,xs,"

static int check_nested(const char *name, const char *prefix, const char *call,
                        unsigned depth, const char *leaf, const char *suffix,
                        RusticStatus expected, long expected_value) {
    char source[4096];
    char *cursor = source;
    size_t prefix_length = strlen(prefix);
    size_t call_length = strlen(call);
    size_t leaf_length = strlen(leaf);
    size_t suffix_length = strlen(suffix);
    unsigned index;
    long value = 99;
    RusticStatus status;

    if (prefix_length + depth * (call_length + 1) + leaf_length + suffix_length >= sizeof(source)) {
        fprintf(stderr, "%s: fixture source too long\n", name);
        return 1;
    }
    memcpy(cursor, prefix, prefix_length);
    cursor += prefix_length;
    for (index = 0; index < depth; index++) {
        memcpy(cursor, call, call_length);
        cursor += call_length;
    }
    memcpy(cursor, leaf, leaf_length);
    cursor += leaf_length;
    memset(cursor, ')', depth);
    cursor += depth;
    memcpy(cursor, suffix, suffix_length + 1);

    status = rustic_eval_expression(source, &value);
    if (status != expected || value != expected_value) {
        fprintf(stderr, "%s: got %s / %ld, wanted %s / %ld\n", name,
                rustic_status_message(status), value, rustic_status_message(expected), expected_value);
        return 1;
    }
    if (rustic_eval_expression("6 * 7", &value) != RUSTIC_OK || value != 42) {
        fprintf(stderr, "%s: next evaluation did not recover\n", name);
        return 1;
    }
    return 0;
}

int main(void) {
    int failed = 0;

    failed |= check_nested("nested scalar arguments", DECLARE_LAST, SCALAR_CALL, 10,
                           "42", "", RUSTIC_OK, 42);
    failed |= check_nested("array roots remap around scalar and function arguments",
                           DECLARE_LAST "let old=[99]; fn bump(x){x+1}; "
                           "fn pick(a,b,c,f,d,e,g,h){f(a[0]*10+d[0]+h)}; "
                           "pick([4],2,3,bump,[1],6,7,", SCALAR_CALL, 10,
                           "{old=0; 0}", ")", RUSTIC_OK, 42);
    failed |= check_nested("deep evaluated argument reaches its own error",
                           DECLARE_LAST, SCALAR_CALL, 10, "1/0", "", RUSTIC_ERR_DIVISION_BY_ZERO, 99);
    failed |= check_nested("short-circuited arguments do not evaluate", "0 && ", SCALAR_CALL, 10,
                           "1/0", "", RUSTIC_OK, 0);
    failed |= check_nested("64 pending array references fit", DECLARE_LAST "let xs=[7]; ", ALIAS_CALL, 9,
                           "last(xs,1,2,3,4,5,6,42)", "", RUSTIC_OK, 42);
    failed |= check_nested("65 pending array references still exceed the root cap",
                           DECLARE_LAST "let xs=[7]; ", ALIAS_CALL, 9,
                           "last(xs,xs,2,3,4,5,6,42)", "", RUSTIC_ERR_TOO_MANY_BINDINGS, 99);
    failed |= check_nested("64 live arrays fit the array store", DECLARE_LAST, NEW_ARRAY_CALL, 9,
                           "len([])", "", RUSTIC_OK, 0);
    failed |= check_nested("65 live arrays still exceed the array store",
                           DECLARE_LAST, NEW_ARRAY_CALL, 9,
                           "len([len([])])", "", RUSTIC_ERR_TOO_MANY_BINDINGS, 99);
    failed |= check_nested("63 scalar calls still fit the factor depth", DECLARE_LAST, SCALAR_CALL, 63,
                           "42", "", RUSTIC_OK, 42);
    failed |= check_nested("64 scalar calls plus a leaf exceed the factor depth",
                           DECLARE_LAST, SCALAR_CALL, 64,
                           "42", "", RUSTIC_ERR_STEP_LIMIT_EXCEEDED, 99);
    return failed;
}
