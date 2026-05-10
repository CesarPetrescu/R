#include "rustic.h"

#include <ctype.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define RUSTIC_MAX_BINDINGS 1024
#define RUSTIC_MAX_FUNCTIONS 8
#define RUSTIC_MAX_IDENTIFIER_LENGTH 31
#define RUSTIC_MAX_PARAMETERS 8
#define RUSTIC_MAX_STEPS 512

enum ValueKind {
    VALUE_INTEGER,
    VALUE_FUNCTION,
};

struct Value {
    enum ValueKind kind;
    long integer;
    size_t function_index;
};

struct Binding {
    char name[RUSTIC_MAX_IDENTIFIER_LENGTH + 1];
    struct Value value;
    size_t scope_depth;
};

struct Function {
    char name[RUSTIC_MAX_IDENTIFIER_LENGTH + 1];
    char parameters[RUSTIC_MAX_PARAMETERS][RUSTIC_MAX_IDENTIFIER_LENGTH + 1];
    size_t parameter_count;
    const char *body_start;
    const char *body_end;
    size_t scope_depth;
};

struct Parser {
    const char *cursor;
    RusticStatus status;
    struct Binding bindings[RUSTIC_MAX_BINDINGS];
    size_t binding_count;
    size_t scope_depth;
    struct Function functions[RUSTIC_MAX_FUNCTIONS];
    size_t function_count;
    size_t steps_remaining;
};

static struct Value integer_value(long integer) {
    struct Value value;

    value.kind = VALUE_INTEGER;
    value.integer = integer;
    value.function_index = 0;
    return value;
}

static struct Value function_value(size_t function_index) {
    struct Value value;

    value.kind = VALUE_FUNCTION;
    value.integer = 0;
    value.function_index = function_index;
    return value;
}

static int value_as_integer(struct Parser *parser, struct Value value, long *out_integer) {
    if (value.kind != VALUE_INTEGER) {
        parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
        return 0;
    }
    *out_integer = value.integer;
    return 1;
}

static int consume_step(struct Parser *parser) {
    if (parser->steps_remaining == 0) {
        parser->status = RUSTIC_ERR_STEP_LIMIT_EXCEEDED;
        return 0;
    }
    parser->steps_remaining--;
    return 1;
}

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

static int lookup_binding(const struct Parser *parser, const char *name, struct Value *out_value) {
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

static int update_binding(struct Parser *parser, const char *name, struct Value value) {
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

static void add_binding(struct Parser *parser, const char *name, struct Value value) {
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

static struct Function *lookup_function(struct Parser *parser, const char *name) {
    size_t index;

    for (index = parser->function_count; index > 0; index--) {
        struct Function *function = &parser->functions[index - 1];
        if (strcmp(function->name, name) == 0) {
            return function;
        }
    }
    return NULL;
}

static struct Function *function_from_value(struct Parser *parser, struct Value value) {
    if (value.kind != VALUE_FUNCTION || value.function_index >= parser->function_count) {
        return NULL;
    }
    return &parser->functions[value.function_index];
}

static void push_scope(struct Parser *parser) {
    parser->scope_depth++;
}

static void pop_scope(struct Parser *parser) {
    while (parser->binding_count > 0 &&
           parser->bindings[parser->binding_count - 1].scope_depth == parser->scope_depth) {
        parser->binding_count--;
    }
    while (parser->function_count > 0 &&
           parser->functions[parser->function_count - 1].scope_depth == parser->scope_depth) {
        parser->function_count--;
    }
    if (parser->scope_depth > 0) {
        parser->scope_depth--;
    }
}

static struct Value parse_expression(struct Parser *parser);
static struct Value parse_statement_sequence(struct Parser *parser, char terminator);

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

static struct Value parse_block_expression(struct Parser *parser) {
    struct Value value = integer_value(0);

    skip_spaces(parser);
    if (*parser->cursor != '{') {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
        return integer_value(0);
    }

    parser->cursor++;
    push_scope(parser);
    value = parse_statement_sequence(parser, '}');
    if (parser->status != RUSTIC_OK) {
        pop_scope(parser);
        return integer_value(0);
    }
    skip_spaces(parser);
    if (*parser->cursor != '}') {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
        pop_scope(parser);
        return integer_value(0);
    }
    parser->cursor++;
    pop_scope(parser);
    return value;
}

static struct Value parse_if_expression(struct Parser *parser) {
    long condition;
    struct Value condition_value;
    struct Value value = integer_value(0);

    parser->cursor += 2;
    condition_value = parse_expression(parser);
    if (parser->status != RUSTIC_OK || !value_as_integer(parser, condition_value, &condition)) {
        return integer_value(0);
    }

    if (condition != 0) {
        value = parse_block_expression(parser);
        if (parser->status != RUSTIC_OK) {
            return integer_value(0);
        }
    } else if (!skip_block(parser)) {
        return integer_value(0);
    }

    skip_spaces(parser);
    if (!cursor_starts_keyword(parser, "else")) {
        parser->status = RUSTIC_ERR_EXPECTED_IDENTIFIER;
        return integer_value(0);
    }
    parser->cursor += 4;

    if (condition == 0) {
        value = parse_block_expression(parser);
        if (parser->status != RUSTIC_OK) {
            return integer_value(0);
        }
    } else if (!skip_block(parser)) {
        return integer_value(0);
    }

    return value;
}

static struct Value parse_while_statement(struct Parser *parser) {
    const char *condition_start;
    long condition;
    struct Value condition_value;
    struct Value value = integer_value(0);

    parser->cursor += 5;
    condition_start = parser->cursor;
    while (parser->status == RUSTIC_OK) {
        parser->cursor = condition_start;
        condition_value = parse_expression(parser);
        if (parser->status != RUSTIC_OK || !value_as_integer(parser, condition_value, &condition)) {
            return integer_value(0);
        }

        if (condition == 0) {
            if (!skip_block(parser)) {
                return integer_value(0);
            }
            return value;
        }

        value = parse_block_expression(parser);
        if (parser->status != RUSTIC_OK) {
            return integer_value(0);
        }
    }

    return value;
}

static struct Value parse_factor(struct Parser *parser) {
    char name[RUSTIC_MAX_IDENTIFIER_LENGTH + 1];
    struct Value arguments[RUSTIC_MAX_PARAMETERS + 1];
    size_t argument_count;
    size_t index;
    struct Value value = integer_value(0);
    long integer;
    char *end = NULL;
    struct Function *function;
    const char *call_return;

    skip_spaces(parser);
    if (*parser->cursor == '!') {
        parser->cursor++;
        value = parse_factor(parser);
        if (parser->status != RUSTIC_OK || !value_as_integer(parser, value, &integer)) {
            return integer_value(0);
        }
        return integer_value(integer == 0 ? 1 : 0);
    }

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
            return integer_value(0);
        }
        skip_spaces(parser);
        if (*parser->cursor != ')') {
            parser->status = RUSTIC_ERR_EXPECTED_CLOSING_PAREN;
            return integer_value(0);
        }
        parser->cursor++;
        return value;
    }

    if (isdigit((unsigned char)*parser->cursor)) {
        integer = strtol(parser->cursor, &end, 10);
        parser->cursor = end;
        return integer_value(integer);
    }

    if (is_identifier_start(*parser->cursor)) {
        if (!parse_identifier(parser, name, sizeof(name))) {
            return integer_value(0);
        }
        skip_spaces(parser);
        if (*parser->cursor == '(') {
            parser->cursor++;
            argument_count = 0;
            skip_spaces(parser);
            if (*parser->cursor != ')') {
                while (parser->status == RUSTIC_OK) {
                    if (argument_count >= RUSTIC_MAX_PARAMETERS) {
                        parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                        return integer_value(0);
                    }
                    arguments[argument_count] = parse_expression(parser);
                    argument_count++;
                    if (parser->status != RUSTIC_OK) {
                        return integer_value(0);
                    }
                    skip_spaces(parser);
                    if (*parser->cursor != ',') {
                        break;
                    }
                    parser->cursor++;
                }
            }
            skip_spaces(parser);
            if (*parser->cursor != ')') {
                parser->status = RUSTIC_ERR_EXPECTED_CLOSING_PAREN;
                return integer_value(0);
            }
            parser->cursor++;

            function = lookup_function(parser, name);
            if (function == NULL) {
                if (!lookup_binding(parser, name, &value)) {
                    parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
                    return integer_value(0);
                }
                function = function_from_value(parser, value);
                if (function == NULL) {
                    parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
                    return integer_value(0);
                }
            }
            if (argument_count != function->parameter_count) {
                parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                return integer_value(0);
            }

            call_return = parser->cursor;
            parser->cursor = function->body_start;
            push_scope(parser);
            for (index = 0; index < argument_count; index++) {
                add_binding(parser, function->parameters[index], arguments[index]);
                if (parser->status != RUSTIC_OK) {
                    pop_scope(parser);
                    parser->cursor = call_return;
                    return integer_value(0);
                }
            }
            value = parse_statement_sequence(parser, '}');
            if (parser->status != RUSTIC_OK) {
                pop_scope(parser);
                parser->cursor = call_return;
                return integer_value(0);
            }
            skip_spaces(parser);
            if (parser->cursor != function->body_end) {
                parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
                pop_scope(parser);
                parser->cursor = call_return;
                return integer_value(0);
            }
            pop_scope(parser);
            parser->cursor = call_return;
            return value;
        }
        if (!lookup_binding(parser, name, &value)) {
            function = lookup_function(parser, name);
            if (function == NULL) {
                parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
                return integer_value(0);
            }
            return function_value((size_t)(function - parser->functions));
        }
        return value;
    }

    parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
    return integer_value(0);
}

static struct Value parse_term(struct Parser *parser) {
    long left;
    long right;
    struct Value value = parse_factor(parser);

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (*parser->cursor != '*') {
            return value;
        }
        if (!value_as_integer(parser, value, &left)) {
            return integer_value(0);
        }
        parser->cursor++;
        value = parse_factor(parser);
        if (parser->status != RUSTIC_OK || !value_as_integer(parser, value, &right)) {
            return integer_value(0);
        }
        value = integer_value(left * right);
    }

    return value;
}

static struct Value parse_additive_expression(struct Parser *parser) {
    long left;
    long right;
    struct Value value = parse_term(parser);
    struct Value right_value;

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (*parser->cursor == '+') {
            if (!value_as_integer(parser, value, &left)) {
                return integer_value(0);
            }
            parser->cursor++;
            right_value = parse_term(parser);
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, right_value, &right)) {
                return integer_value(0);
            }
            value = integer_value(left + right);
        } else if (*parser->cursor == '-') {
            if (!value_as_integer(parser, value, &left)) {
                return integer_value(0);
            }
            parser->cursor++;
            right_value = parse_term(parser);
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, right_value, &right)) {
                return integer_value(0);
            }
            value = integer_value(left - right);
        } else if (*parser->cursor == '*') {
            parser->status = RUSTIC_ERR_EXPECTED_OPERATOR;
        } else {
            return value;
        }
    }

    return value;
}

static struct Value parse_expression(struct Parser *parser) {
    long left;
    long right;
    struct Value value = parse_additive_expression(parser);
    struct Value right_value;

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (parser->cursor[0] == '=' && parser->cursor[1] == '=') {
            if (!value_as_integer(parser, value, &left)) {
                return integer_value(0);
            }
            parser->cursor += 2;
            right_value = parse_additive_expression(parser);
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, right_value, &right)) {
                return integer_value(0);
            }
            value = integer_value((left == right) ? 1 : 0);
        } else if (parser->cursor[0] == '!' && parser->cursor[1] == '=') {
            if (!value_as_integer(parser, value, &left)) {
                return integer_value(0);
            }
            parser->cursor += 2;
            right_value = parse_additive_expression(parser);
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, right_value, &right)) {
                return integer_value(0);
            }
            value = integer_value((left != right) ? 1 : 0);
        } else if (parser->cursor[0] == '<' && parser->cursor[1] == '=') {
            if (!value_as_integer(parser, value, &left)) {
                return integer_value(0);
            }
            parser->cursor += 2;
            right_value = parse_additive_expression(parser);
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, right_value, &right)) {
                return integer_value(0);
            }
            value = integer_value((left <= right) ? 1 : 0);
        } else if (parser->cursor[0] == '>' && parser->cursor[1] == '=') {
            if (!value_as_integer(parser, value, &left)) {
                return integer_value(0);
            }
            parser->cursor += 2;
            right_value = parse_additive_expression(parser);
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, right_value, &right)) {
                return integer_value(0);
            }
            value = integer_value((left >= right) ? 1 : 0);
        } else if (*parser->cursor == '<') {
            if (!value_as_integer(parser, value, &left)) {
                return integer_value(0);
            }
            parser->cursor++;
            right_value = parse_additive_expression(parser);
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, right_value, &right)) {
                return integer_value(0);
            }
            value = integer_value((left < right) ? 1 : 0);
        } else if (*parser->cursor == '>') {
            if (!value_as_integer(parser, value, &left)) {
                return integer_value(0);
            }
            parser->cursor++;
            right_value = parse_additive_expression(parser);
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, right_value, &right)) {
                return integer_value(0);
            }
            value = integer_value((left > right) ? 1 : 0);
        } else if (*parser->cursor == '=' || *parser->cursor == '!') {
            parser->status = RUSTIC_ERR_EXPECTED_OPERATOR;
            return integer_value(0);
        } else {
            return value;
        }
    }

    return value;
}

static void parse_let_statement(struct Parser *parser) {
    char name[RUSTIC_MAX_IDENTIFIER_LENGTH + 1];
    struct Value value;

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

static void parse_function_declaration(struct Parser *parser) {
    struct Function *function;
    const char *block_start;

    if (parser->function_count >= RUSTIC_MAX_FUNCTIONS) {
        parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
        return;
    }

    function = &parser->functions[parser->function_count];
    parser->cursor += 2;
    if (!parse_identifier(parser, function->name, sizeof(function->name))) {
        return;
    }

    skip_spaces(parser);
    if (*parser->cursor != '(') {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_PAREN;
        return;
    }
    parser->cursor++;
    function->parameter_count = 0;
    skip_spaces(parser);
    if (*parser->cursor != ')') {
        while (parser->status == RUSTIC_OK) {
            if (function->parameter_count >= RUSTIC_MAX_PARAMETERS) {
                parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                return;
            }
            if (!parse_identifier(
                    parser,
                    function->parameters[function->parameter_count],
                    sizeof(function->parameters[function->parameter_count]))) {
                return;
            }
            function->parameter_count++;
            skip_spaces(parser);
            if (*parser->cursor != ',') {
                break;
            }
            parser->cursor++;
        }
    }
    skip_spaces(parser);
    if (*parser->cursor != ')') {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_PAREN;
        return;
    }
    parser->cursor++;

    skip_spaces(parser);
    if (*parser->cursor != '{') {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
        return;
    }
    block_start = parser->cursor;
    function->body_start = block_start + 1;
    if (!skip_block(parser)) {
        return;
    }
    function->body_end = parser->cursor - 1;
    function->scope_depth = parser->scope_depth;
    parser->function_count++;

    skip_spaces(parser);
    if (*parser->cursor != ';') {
        parser->status = RUSTIC_ERR_EXPECTED_SEMICOLON;
        return;
    }
    parser->cursor++;
}

static int parse_assignment_statement(struct Parser *parser, struct Value *out_value) {
    const char *statement_start = parser->cursor;
    char name[RUSTIC_MAX_IDENTIFIER_LENGTH + 1];
    struct Value value;
    struct Value existing_value;

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

static struct Value parse_statement_sequence(struct Parser *parser, char terminator) {
    struct Value value = integer_value(0);
    int saw_statement = 0;

    while (parser->status == RUSTIC_OK) {
        if (!consume_step(parser)) {
            return integer_value(0);
        }
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
                return integer_value(0);
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

        if (cursor_starts_keyword(parser, "fn")) {
            parse_function_declaration(parser);
            saw_statement = 1;
            continue;
        }

        if (cursor_starts_keyword(parser, "while")) {
            value = parse_while_statement(parser);
            if (parser->status != RUSTIC_OK) {
                return integer_value(0);
            }
            saw_statement = 1;

            skip_spaces(parser);
            if (*parser->cursor != ';') {
                return value;
            }
            parser->cursor++;
            continue;
        }

        if (parse_assignment_statement(parser, &value)) {
            if (parser->status != RUSTIC_OK) {
                return integer_value(0);
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
            return integer_value(0);
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

static struct Value parse_program(struct Parser *parser) {
    return parse_statement_sequence(parser, '\0');
}
RusticStatus rustic_eval_expression(const char *source, long *out_value) {
    struct Parser parser;
    struct Value value;
    long integer;

    if (source == NULL || out_value == NULL) {
        return RUSTIC_ERR_EXPECTED_INTEGER;
    }

    parser.cursor = source;
    parser.status = RUSTIC_OK;
    parser.binding_count = 0;
    parser.scope_depth = 0;
    parser.function_count = 0;
    parser.steps_remaining = RUSTIC_MAX_STEPS;
    value = parse_program(&parser);
    if (parser.status != RUSTIC_OK) {
        return parser.status;
    }

    skip_spaces(&parser);
    if (*parser.cursor != '\0') {
        return RUSTIC_ERR_TRAILING_INPUT;
    }

    if (!value_as_integer(&parser, value, &integer)) {
        return parser.status;
    }

    *out_value = integer;
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
    case RUSTIC_ERR_WRONG_ARGUMENT_COUNT:
        return "wrong argument count";
    case RUSTIC_ERR_STEP_LIMIT_EXCEEDED:
        return "step limit exceeded";
    default:
        return "unknown rustic interpreter error";
    }
}
