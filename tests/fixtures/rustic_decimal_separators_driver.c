#include "rustic.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    char max_digits[3 * sizeof(long) + 4];
    char grouped[3 * sizeof(long) + 8];
    char min_digits[3 * sizeof(long) + 4];
    char source[3 * sizeof(long) + 64];
    long result = 99;
    RusticStatus status;

    snprintf(max_digits, sizeof(max_digits), "%ld", LONG_MAX);
    snprintf(grouped, sizeof(grouped), "%c_%s", max_digits[0], max_digits + 1);
    status = rustic_eval_expression(grouped, &result);
    if (status != RUSTIC_OK || result != LONG_MAX) return 1;

    snprintf(min_digits, sizeof(min_digits), "%ld", LONG_MIN);
    snprintf(grouped, sizeof(grouped), "-%c_%s", min_digits[1], min_digits + 2);
    status = rustic_eval_expression(grouped, &result);
    if (status != RUSTIC_OK || result != LONG_MIN) return 7;

    snprintf(source, sizeof(source), "%c_%s", max_digits[0], max_digits + 1);
    status = rustic_eval_expression(source, &result);
    if (status != RUSTIC_OK || result != LONG_MAX) return 8;
    snprintf(source, sizeof(source), "%lu_0", (unsigned long)LONG_MAX + 1UL);
    status = rustic_eval_expression(source, &result);
    if (status != RUSTIC_ERR_INTEGER_OVERFLOW || result != LONG_MAX) return 9;

    snprintf(source, sizeof(source), "-%s_0", max_digits);
    result = 23;
    status = rustic_eval_expression(source, &result);
    if (status != RUSTIC_ERR_INTEGER_OVERFLOW || result != 23 ||
        strcmp(rustic_status_message(status), "integer overflow") != 0) return 2;

    snprintf(source, sizeof(source), "match -1_2 { -1_2 => 7, _ => 0 }");
    status = rustic_eval_expression(source, &result);
    if (status != RUSTIC_OK || result != 7) return 3;

    snprintf(source, sizeof(source), "0 && %s_0", max_digits);
    status = rustic_eval_expression(source, &result);
    if (status != RUSTIC_OK || result != 0) return 4;

    status = rustic_eval_expression("1__2", &result);
    if (status != RUSTIC_ERR_EXPECTED_SEMICOLON || result != 0) return 5;
    status = rustic_eval_expression("2_5", &result);
    if (status != RUSTIC_OK || result != 25) return 6;

    puts("C API decimal separators, bounds, laziness, output and recovery: ok");
    return 0;
}
