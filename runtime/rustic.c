#include "rustic.h"

#include <ctype.h>
#include <stddef.h>
#include <stdlib.h>

struct Parser {
    const char *cursor;
    RusticStatus status;
};

static void skip_spaces(struct Parser *parser) {
    while (isspace((unsigned char)*parser->cursor)) {
        parser->cursor++;
    }
}

static long parse_integer(struct Parser *parser) {
    char *end = NULL;
    long value;

    skip_spaces(parser);
    if (!isdigit((unsigned char)*parser->cursor)) {
        parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
        return 0;
    }

    value = strtol(parser->cursor, &end, 10);
    parser->cursor = end;
    return value;
}

static long parse_term(struct Parser *parser) {
    long value = parse_integer(parser);

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (*parser->cursor != '*') {
            return value;
        }
        parser->cursor++;
        value *= parse_integer(parser);
    }

    return value;
}

static long parse_expression(struct Parser *parser) {
    long value = parse_term(parser);

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (*parser->cursor == '+') {
            parser->cursor++;
            value += parse_term(parser);
        } else if (*parser->cursor == '*') {
            parser->status = RUSTIC_ERR_EXPECTED_OPERATOR;
        } else {
            return value;
        }
    }

    return value;
}

RusticStatus rustic_eval_expression(const char *source, long *out_value) {
    struct Parser parser;
    long value;

    if (source == NULL || out_value == NULL) {
        return RUSTIC_ERR_EXPECTED_INTEGER;
    }

    parser.cursor = source;
    parser.status = RUSTIC_OK;
    value = parse_expression(&parser);
    if (parser.status != RUSTIC_OK) {
        return parser.status;
    }

    skip_spaces(&parser);
    if (*parser.cursor != '\0') {
        return RUSTIC_ERR_TRAILING_INPUT;
    }

    *out_value = value;
    return RUSTIC_OK;
}

const char *rustic_status_message(RusticStatus status) {
    switch (status) {
    case RUSTIC_OK:
        return "ok";
    case RUSTIC_ERR_EXPECTED_INTEGER:
        return "expected integer";
    case RUSTIC_ERR_EXPECTED_OPERATOR:
        return "expected operator";
    case RUSTIC_ERR_TRAILING_INPUT:
        return "trailing input";
    default:
        return "unknown rustic interpreter error";
    }
}
