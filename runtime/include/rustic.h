#ifndef RUSTIC_H
#define RUSTIC_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum RusticStatus {
    RUSTIC_OK = 0,
    RUSTIC_ERR_EXPECTED_INTEGER = 1,
    RUSTIC_ERR_EXPECTED_OPERATOR = 2,
    RUSTIC_ERR_TRAILING_INPUT = 3,
    RUSTIC_ERR_EXPECTED_IDENTIFIER = 4,
    RUSTIC_ERR_EXPECTED_EQUALS = 5,
    RUSTIC_ERR_EXPECTED_SEMICOLON = 6,
    RUSTIC_ERR_UNDEFINED_IDENTIFIER = 7,
    RUSTIC_ERR_TOO_MANY_BINDINGS = 8,
    RUSTIC_ERR_EXPECTED_CLOSING_PAREN = 9,
    RUSTIC_ERR_EXPECTED_CLOSING_BRACE = 10,
    RUSTIC_ERR_WRONG_ARGUMENT_COUNT = 11,
    RUSTIC_ERR_STEP_LIMIT_EXCEEDED = 12,
    RUSTIC_ERR_DIVISION_BY_ZERO = 13,
    RUSTIC_ERR_LOOP_CONTROL_OUTSIDE_LOOP = 14,
    RUSTIC_ERR_NO_MATCHING_MATCH_ARM = 15,
    RUSTIC_ERR_EXPECTED_CLOSING_BRACKET = 16,
    RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS = 17,
    RUSTIC_ERR_EXPECTED_ARRAY = 18,
    RUSTIC_ERR_EMPTY_ARRAY = 19,
    RUSTIC_ERR_ARRAY_LENGTH_MISMATCH = 20,
    RUSTIC_ERR_INTEGER_OVERFLOW = 21,
} RusticStatus;

/* Evaluated expression +, binary -, and * report INTEGER_OVERFLOW when the
 * result is outside host long; / and % report it for LONG_MIN with divisor -1.
 * sum(array), prefix_sum(array), window_sum(array, n),
 * moving_average_sum(array, n), and chunk_sum(array, n) check each
 * intermediate addition. adjacent_diff(array) checks each subtraction.
 * variance_sum(array) checks mean accumulation, each difference and square,
 * and the sum of squares. median(array) checks the addition of the two
 * middle elements before dividing an even-length median. top_sum(array, n)
 * checks each selected addition after sorting descending, including a
 * prefix that would overflow before later selected values could cancel it.
 * weighted_score(array, fn) checks each integer callback result before
 * adding it to the running score, including a prefix that would overflow
 * before later callback results could cancel it. histogram_pairs_score(values,
 * counts) checks each pair multiplication and each left-to-right sum before
 * signed overflow, even when a later pair could cancel the excess.
 * histogram_distance_score(values, counts, expected) and
 * histogram_within_distance(values, counts, expected, limit) check each
 * count-minus-expected-frequency subtraction, LONG_MIN absolute distance,
 * left-to-right score addition, and increment for an unlisted expected
 * element before host-long overflow. Both report INTEGER_OVERFLOW for an
 * overflowing prefix, even if the distance limit would otherwise accept it.
 * outlier_score(array, min, max) checks each distance subtraction and
 * left-to-right nonnegative score addition before host-long overflow.
 * Other array/statistics arithmetic remains unchecked for overflow.
 * On any error, *out_value is left unchanged. */
RusticStatus rustic_eval_expression(const char *source, long *out_value);
const char *rustic_status_message(RusticStatus status);

#ifdef __cplusplus
}
#endif

#endif
