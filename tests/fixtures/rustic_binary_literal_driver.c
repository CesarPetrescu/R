#include "rustic.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

static void binary_digits(unsigned long value, char *buffer, size_t size) {
    char reversed[sizeof(unsigned long) * CHAR_BIT + 1];
    size_t count = 0;
    size_t index;
    do {
        reversed[count++] = (value & 1UL) ? '1' : '0';
        value >>= 1;
    } while (value != 0);
    if (count + 1 > size) {
        buffer[0] = '\0';
        return;
    }
    for (index = 0; index < count; index++) buffer[index] = reversed[count - 1 - index];
    buffer[count] = '\0';
}

static int check(const char *source, RusticStatus expected, long expected_value) {
    long output = 12345;
    RusticStatus status = rustic_eval_expression(source, &output);
    if (status != expected || output != expected_value) {
        fprintf(stderr, "binary contract failed: %s (%s, %ld)\n",
                source, rustic_status_message(status), output);
        return 0;
    }
    return 1;
}

int main(void) {
    char source[512];
    char max_digits[sizeof(unsigned long) * CHAR_BIT + 1];
    char min_magnitude[sizeof(unsigned long) * CHAR_BIT + 1];
    char over_min[sizeof(unsigned long) * CHAR_BIT + 1];
    unsigned long beyond_positive = (unsigned long)LONG_MAX + 1UL;
    binary_digits((unsigned long)LONG_MAX, max_digits, sizeof(max_digits));
    binary_digits(beyond_positive, min_magnitude, sizeof(min_magnitude));
    binary_digits(beyond_positive + 1UL, over_min, sizeof(over_min));

    snprintf(source, sizeof(source), "0b%s", max_digits);
    if (!check(source, RUSTIC_OK, LONG_MAX)) return 1;
    snprintf(source, sizeof(source), "-0b%s", min_magnitude);
    if (!check(source, RUSTIC_OK, LONG_MIN)) return 2;
    snprintf(source, sizeof(source), "0b%s", min_magnitude);
    if (!check(source, RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 3;
    snprintf(source, sizeof(source), "-0b%s", over_min);
    if (!check(source, RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 4;
    snprintf(source, sizeof(source), "match 0 { 0 => 1, 0b%s => 2 }", min_magnitude);
    if (!check(source, RUSTIC_ERR_INTEGER_OVERFLOW, 12345)) return 5;
    snprintf(source, sizeof(source), "match -0b%s { -0b%s => 7, _ => 0 }",
             min_magnitude, min_magnitude);
    if (!check(source, RUSTIC_OK, 7)) return 6;
    if (!check("0 && 0b_1", RUSTIC_ERR_EXPECTED_INTEGER, 12345)) return 7;
    if (!check("0 && 0b1111111111111111111111111111111111111111111111111111111111111111111111111111111111111111", RUSTIC_OK, 0)) return 8;
    if (!check("let x = 0b101010; x", RUSTIC_OK, 42)) return 9;
    if (!check("0b10_", RUSTIC_ERR_EXPECTED_SEMICOLON, 12345)) return 10;
    if (strcmp(rustic_status_message(RUSTIC_ERR_INTEGER_OVERFLOW), "integer overflow") != 0) return 11;
    return 0;
}
