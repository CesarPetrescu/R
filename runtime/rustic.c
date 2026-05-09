#include "rustic.h"

#include <ctype.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define RUSTIC_MAX_BINDINGS 16
#define RUSTIC_MAX_IDENTIFIER_LENGTH 31

struct Binding {
    char name[RUSTIC_MAX_IDENTIFIER_LENGTH + 1];
    long value;
    size_t scope_depth;
};

struct Parser {
    const char *cursor;
    RusticStatus status;
    struct Binding bindings[RUSTIC_MAX_BINDINGS];
    size_t binding_count;
    size_t scope_depth;
};

static void skip_spaces(struct Parser *parser) {
    while (isspace((unsigned char)*parser->cursor)) {
        parser->cursor++;
    }
}

static int is_identifier_start(char character) {
    return isalpha((unsigned char)character) || character == '_';
}

static int is_identifier_continue(char character) {
    return isalnum((unsigned char)character) || character == '_';
}

static int parse_identifier(struct Parser *parser, char *out_name, size_t out_size) {
    size_t length = 0;

    skip_spaces(parser);
    if (!is_identifier_start(*parser->cursor)) {
        parser->status = RUSTIC_ERR_EXPECTED_IDENTIFIER;
        return 0;
    }

    while (is_identifier_continue(*parser->cursor)) {
        if (length + 1 < out_size) {
            out_name[length] = *parser->cursor;
            length++;
        }
        parser->cursor++;
    }
    out_name[length] = '\0';
    return 1;
}

static int cursor_starts_keyword(const struct Parser *parser, const char *keyword) {
    size_t length = strlen(keyword);

    return strncmp(parser->cursor, keyword, length) == 0 &&
           !is_identifier_continue(parser->cursor[length]);
}

static int lookup_binding(const struct Parser *parser, const char *name, long *out_value) {
    size_t index;

    for (index = parser->binding_count; index > 0; index--) {
        const struct Binding *binding = &parser->bindings[index - 1];
        if (strcmp(binding->name, name) == 0) {
            *out_value = binding->value;
            return 1;
        }
    }
    return 0;
}

static int update_binding(struct Parser *parser, const char *name, long value) {
    size_t index;

    for (index = parser->binding_count; index > 0; index--) {
        struct Binding *binding = &parser->bindings[index - 1];
        if (strcmp(binding->name, name) == 0) {
            binding->value = value;
            return 1;
        }
    }
    parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
    return 0;
}

static void add_binding(struct Parser *parser, const char *name, long value) {
    if (parser->binding_count >= RUSTIC_MAX_BINDINGS) {
        parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
        return;
    }

    strncpy(parser->bindings[parser->binding_count].name, name, RUSTIC_MAX_IDENTIFIER_LENGTH);
    parser->bindings[parser->binding_count].name[RUSTIC_MAX_IDENTIFIER_LENGTH] = '\0';
    parser->bindings[parser->binding_count].value = value;
    parser->bindings[parser->binding_count].scope_depth = parser->scope_depth;
    parser->binding_count++;
}

static void push_scope(struct Parser *parser) {
    parser->scope_depth++;
}

static void pop_scope(struct Parser *parser) {
    while (parser->binding_count > 0 &&
           parser->bindings[parser->binding_count - 1].scope_depth == parser->scope_depth) {
        parser->binding_count--;
    }
    if (parser->scope_depth > 0) {
        parser->scope_depth--;
    }
}

static long parse_expression(struct Parser *parser);
static long parse_statement_sequence(struct Parser *parser, char terminator);

static int skip_block(struct Parser *parser) {
    size_t depth = 0;

    skip_spaces(parser);
    if (*parser->cursor != '{') {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
        return 0;
    }

    while (*parser->cursor != '\0') {
        if (*parser->cursor == '{') {
            depth++;
        } else if (*parser->cursor == '}') {
            depth--;
            parser->cursor++;
            if (depth == 0) {
                return 1;
            }
            continue;
        }
        parser->cursor++;
    }

    parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
    return 0;
}

static long parse_block_expression(struct Parser *parser) {
    long value;

    skip_spaces(parser);
    if (*parser->cursor != '{') {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
        return 0;
    }

    parser->cursor++;
    push_scope(parser);
    value = parse_statement_sequence(parser, '}');
    if (parser->status != RUSTIC_OK) {
        pop_scope(parser);
        return 0;
    }
    skip_spaces(parser);
    if (*parser->cursor != '}') {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
        pop_scope(parser);
        return 0;
    }
    parser->cursor++;
    pop_scope(parser);
    return value;
}

static long parse_if_expression(struct Parser *parser) {
    long condition;
    long value;

    parser->cursor += 2;
    condition = parse_expression(parser);
    if (parser->status != RUSTIC_OK) {
        return 0;
    }

    if (condition != 0) {
        value = parse_block_expression(parser);
        if (parser->status != RUSTIC_OK) {
            return 0;
        }
    } else if (!skip_block(parser)) {
        return 0;
    }

    skip_spaces(parser);
    if (!cursor_starts_keyword(parser, "else")) {
        parser->status = RUSTIC_ERR_EXPECTED_IDENTIFIER;
        return 0;
    }
    parser->cursor += 4;

    if (condition == 0) {
        value = parse_block_expression(parser);
        if (parser->status != RUSTIC_OK) {
            return 0;
        }
    } else if (!skip_block(parser)) {
        return 0;
    }

    return value;
}

static long parse_factor(struct Parser *parser) {
    char name[RUSTIC_MAX_IDENTIFIER_LENGTH + 1];
    long value;
    char *end = NULL;

    skip_spaces(parser);
    if (*parser->cursor == '{') {
        return parse_block_expression(parser);
    }

    if (cursor_starts_keyword(parser, "if")) {
        return parse_if_expression(parser);
    }

    if (*parser->cursor == '(') {
        parser->cursor++;
        value = parse_expression(parser);
        if (parser->status != RUSTIC_OK) {
            return 0;
        }
        skip_spaces(parser);
        if (*parser->cursor != ')') {
            parser->status = RUSTIC_ERR_EXPECTED_CLOSING_PAREN;
            return 0;
        }
        parser->cursor++;
        return value;
    }

    if (isdigit((unsigned char)*parser->cursor)) {
        value = strtol(parser->cursor, &end, 10);
        parser->cursor = end;
        return value;
    }

    if (is_identifier_start(*parser->cursor)) {
        if (!parse_identifier(parser, name, sizeof(name))) {
            return 0;
        }
        if (!lookup_binding(parser, name, &value)) {
            parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
            return 0;
        }
        return value;
    }

    parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
    return 0;
}

static long parse_term(struct Parser *parser) {
    long value = parse_factor(parser);

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (*parser->cursor != '*') {
            return value;
        }
        parser->cursor++;
        value *= parse_factor(parser);
    }

    return value;
}

static long parse_additive_expression(struct Parser *parser) {
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

static long parse_expression(struct Parser *parser) {
    long right;
    long value = parse_additive_expression(parser);

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (parser->cursor[0] == '=' && parser->cursor[1] == '=') {
            parser->cursor += 2;
            right = parse_additive_expression(parser);
            value = (value == right) ? 1 : 0;
        } else if (parser->cursor[0] == '!' && parser->cursor[1] == '=') {
            parser->cursor += 2;
            right = parse_additive_expression(parser);
            value = (value != right) ? 1 : 0;
        } else if (parser->cursor[0] == '<' && parser->cursor[1] == '=') {
            parser->cursor += 2;
            right = parse_additive_expression(parser);
            value = (value <= right) ? 1 : 0;
        } else if (parser->cursor[0] == '>' && parser->cursor[1] == '=') {
            parser->cursor += 2;
            right = parse_additive_expression(parser);
            value = (value >= right) ? 1 : 0;
        } else if (*parser->cursor == '<') {
            parser->cursor++;
            right = parse_additive_expression(parser);
            value = (value < right) ? 1 : 0;
        } else if (*parser->cursor == '>') {
            parser->cursor++;
            right = parse_additive_expression(parser);
            value = (value > right) ? 1 : 0;
        } else if (*parser->cursor == '=' || *parser->cursor == '!') {
            parser->status = RUSTIC_ERR_EXPECTED_OPERATOR;
            return 0;
        } else {
            return value;
        }
    }

    return value;
}

static void parse_let_statement(struct Parser *parser) {
    char name[RUSTIC_MAX_IDENTIFIER_LENGTH + 1];
    long value;

    parser->cursor += 3;
    if (!parse_identifier(parser, name, sizeof(name))) {
        return;
    }

    skip_spaces(parser);
    if (*parser->cursor != '=') {
        parser->status = RUSTIC_ERR_EXPECTED_EQUALS;
        return;
    }
    parser->cursor++;

    value = parse_expression(parser);
    if (parser->status != RUSTIC_OK) {
        return;
    }

    skip_spaces(parser);
    if (*parser->cursor != ';') {
        parser->status = RUSTIC_ERR_EXPECTED_SEMICOLON;
        return;
    }
    parser->cursor++;
    add_binding(parser, name, value);
}

static int parse_assignment_statement(struct Parser *parser, long *out_value) {
    const char *statement_start = parser->cursor;
    char name[RUSTIC_MAX_IDENTIFIER_LENGTH + 1];
    long value;
    long existing_value;

    if (!is_identifier_start(*parser->cursor)) {
        return 0;
    }

    if (!parse_identifier(parser, name, sizeof(name))) {
        return 0;
    }

    skip_spaces(parser);
    if (*parser->cursor != '=' || parser->cursor[1] == '=') {
        parser->cursor = statement_start;
        parser->status = RUSTIC_OK;
        return 0;
    }
    parser->cursor++;

    if (!lookup_binding(parser, name, &existing_value)) {
        parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
        return 1;
    }

    value = parse_expression(parser);
    if (parser->status != RUSTIC_OK) {
        return 1;
    }

    update_binding(parser, name, value);
    *out_value = value;
    return 1;
}

static long parse_statement_sequence(struct Parser *parser, char terminator) {
    long value = 0;
    int saw_statement = 0;

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (terminator != '\0' && *parser->cursor == terminator) {
            if (!saw_statement) {
                parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
            }
            return value;
        }
        if (*parser->cursor == '\0') {
            if (terminator != '\0') {
                parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
                return 0;
            }
            if (!saw_statement) {
                parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
            }
            return value;
        }

        if (cursor_starts_keyword(parser, "let")) {
            parse_let_statement(parser);
            saw_statement = 1;
            continue;
        }

        if (parse_assignment_statement(parser, &value)) {
            if (parser->status != RUSTIC_OK) {
                return 0;
            }
            saw_statement = 1;

            skip_spaces(parser);
            if (*parser->cursor != ';') {
                return value;
            }
            parser->cursor++;
            continue;
        }

        value = parse_expression(parser);
        if (parser->status != RUSTIC_OK) {
            return 0;
        }
        saw_statement = 1;

        skip_spaces(parser);
        if (*parser->cursor != ';') {
            return value;
        }
        parser->cursor++;
    }

    return value;
}

static long parse_program(struct Parser *parser) {
    return parse_statement_sequence(parser, '\0');
}

RusticStatus rustic_eval_expression(const char *source, long *out_value) {
    struct Parser parser;
    long value;

    if (source == NULL || out_value == NULL) {
        return RUSTIC_ERR_EXPECTED_INTEGER;
    }

    parser.cursor = source;
    parser.status = RUSTIC_OK;
    parser.binding_count = 0;
    parser.scope_depth = 0;
    value = parse_program(&parser);
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
    case RUSTIC_ERR_EXPECTED_IDENTIFIER:
        return "expected identifier";
    case RUSTIC_ERR_EXPECTED_EQUALS:
        return "expected equals";
    case RUSTIC_ERR_EXPECTED_SEMICOLON:
        return "expected semicolon";
    case RUSTIC_ERR_UNDEFINED_IDENTIFIER:
        return "undefined identifier";
    case RUSTIC_ERR_TOO_MANY_BINDINGS:
        return "too many bindings";
    case RUSTIC_ERR_EXPECTED_CLOSING_PAREN:
        return "expected closing parenthesis";
    case RUSTIC_ERR_EXPECTED_CLOSING_BRACE:
        return "expected closing brace";
    default:
        return "unknown rustic interpreter error";
    }
}
