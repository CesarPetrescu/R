#include "rustic.h"

#include <stdio.h>

int main(void) {
    static const struct {
        const char *source;
        RusticStatus status;
    } cases[] = {
        {"let true = 1 / 0; true", RUSTIC_ERR_EXPECTED_IDENTIFIER},
        {"fn false() { 1 }; 0", RUSTIC_ERR_EXPECTED_IDENTIFIER},
        {"fn f(true) { 1 }; 0", RUSTIC_ERR_EXPECTED_IDENTIFIER},
        {"true = 0", RUSTIC_ERR_EXPECTED_OPERATOR},
        {"false()", RUSTIC_ERR_EXPECTED_SEMICOLON},
        {"0 && false()", RUSTIC_ERR_EXPECTED_SEMICOLON},
        {"false[0] = 7", RUSTIC_ERR_EXPECTED_ARRAY},
        {"true && 1 / 0", RUSTIC_ERR_DIVISION_BY_ZERO},
        {"true || false[", RUSTIC_ERR_EXPECTED_INTEGER},
        {"match 0 { false => 1 }", RUSTIC_ERR_EXPECTED_INTEGER},
        {"while true { 1 }; 42", RUSTIC_ERR_STEP_LIMIT_EXCEEDED},
    };
    long out = 123;
    size_t i;

    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        RusticStatus actual = rustic_eval_expression(cases[i].source, &out);
        if (actual != cases[i].status || out != 123) {
            fprintf(stderr, "%s: wanted status '%s', got '%s' (out = %ld)\n", cases[i].source,
                    rustic_status_message(cases[i].status), rustic_status_message(actual), out);
            return 1;
        }
    }
    if (rustic_eval_expression("if true && !false { 42 } else { 0 }", &out) != RUSTIC_OK || out != 42) {
        fprintf(stderr, "valid follow-up evaluation did not return 42\n");
        return 2;
    }
    return 0;
}
