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
} RusticStatus;

RusticStatus rustic_eval_expression(const char *source, long *out_value);
const char *rustic_status_message(RusticStatus status);

#ifdef __cplusplus
}
#endif

#endif
