#include "rustic.h"

#include <ctype.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define RUSTIC_MAX_BINDINGS 1024
#define RUSTIC_MAX_FUNCTIONS 8
#define RUSTIC_MAX_IDENTIFIER_LENGTH 63
#define RUSTIC_MAX_ARRAYS 64
#define RUSTIC_MAX_ARRAY_ELEMENTS 16
#define RUSTIC_MAX_PARAMETERS 8
#define RUSTIC_MAX_STEPS 512
#define RUSTIC_MAX_ARRAY_ROOTS 64

enum ValueKind {
    VALUE_INTEGER,
    VALUE_FUNCTION,
    VALUE_ARRAY,
};

struct Value {
    enum ValueKind kind;
    long integer;
    size_t function_index;
    size_t function_id;
    size_t array_index;
    size_t array_id;
};

enum LoopControl {
    LOOP_CONTROL_NONE,
    LOOP_CONTROL_BREAK,
    LOOP_CONTROL_CONTINUE,
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
    size_t id;
};

struct ArrayValue {
    long elements[RUSTIC_MAX_ARRAY_ELEMENTS];
    size_t element_count;
    size_t scope_depth;
    size_t id;
    int under_construction;
};

struct Parser {
    const char *cursor;
    RusticStatus status;
    struct Binding bindings[RUSTIC_MAX_BINDINGS];
    size_t binding_count;
    size_t scope_depth;
    struct Function functions[RUSTIC_MAX_FUNCTIONS];
    size_t function_count;
    size_t next_function_id;
    struct ArrayValue arrays[RUSTIC_MAX_ARRAYS];
    size_t array_count;
    size_t next_array_id;
    size_t steps_remaining;
    size_t loop_depth;
    enum LoopControl loop_control;
    struct Value *array_roots;
    size_t array_root_count;
};

static struct Value integer_value(long integer) {
    struct Value value;

    value.kind = VALUE_INTEGER;
    value.integer = integer;
    value.function_index = 0;
    value.function_id = 0;
    value.array_index = 0;
    value.array_id = 0;
    return value;
}

static struct Value function_value(size_t function_index, size_t function_id) {
    struct Value value;

    value.kind = VALUE_FUNCTION;
    value.integer = 0;
    value.function_index = function_index;
    value.function_id = function_id;
    value.array_index = 0;
    value.array_id = 0;
    return value;
}

static struct Value array_value(size_t array_index, size_t array_id) {
    struct Value value;

    value.kind = VALUE_ARRAY;
    value.integer = 0;
    value.function_index = 0;
    value.function_id = 0;
    value.array_index = array_index;
    value.array_id = array_id;
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
    if (parser->functions[value.function_index].id != value.function_id) {
        return NULL;
    }
    return &parser->functions[value.function_index];
}

static struct ArrayValue *array_from_value(struct Parser *parser, struct Value value) {
    if (value.kind != VALUE_ARRAY || value.array_index >= parser->array_count) {
        return NULL;
    }
    if (parser->arrays[value.array_index].id != value.array_id) {
        return NULL;
    }
    return &parser->arrays[value.array_index];
}

static struct ArrayValue *array_by_id(struct Parser *parser, size_t array_id, size_t *out_index) {
    size_t index;

    for (index = 0; index < parser->array_count; index++) {
        if (parser->arrays[index].id == array_id) {
            if (out_index != NULL) {
                *out_index = index;
            }
            return &parser->arrays[index];
        }
    }
    return NULL;
}

static void push_scope(struct Parser *parser) {
    parser->scope_depth++;
}

static int binding_references_array(const struct Parser *parser, size_t array_id) {
    size_t index;

    for (index = 0; index < parser->binding_count; index++) {
        const struct Binding *binding = &parser->bindings[index];
        if (binding->value.kind == VALUE_ARRAY && binding->value.array_id == array_id) {
            return 1;
        }
    }
    return 0;
}

static int parser_roots_reference_array(const struct Parser *parser, size_t array_id) {
    size_t index;

    for (index = 0; index < parser->array_root_count; index++) {
        const struct Value *root = &parser->array_roots[index];
        if (root->kind == VALUE_ARRAY && root->array_id == array_id) {
            return 1;
        }
    }
    return 0;
}

static void remap_parser_root_array_indices(struct Parser *parser, size_t array_id, size_t array_index) {
    size_t index;

    for (index = 0; index < parser->array_root_count; index++) {
        struct Value *root = &parser->array_roots[index];
        if (root->kind == VALUE_ARRAY && root->array_id == array_id) {
            root->array_index = array_index;
        }
    }
}

static void remap_binding_array_indices(struct Parser *parser, size_t array_id, size_t array_index) {
    size_t index;

    for (index = 0; index < parser->binding_count; index++) {
        struct Binding *binding = &parser->bindings[index];
        if (binding->value.kind == VALUE_ARRAY && binding->value.array_id == array_id) {
            binding->value.array_index = array_index;
        }
    }
}

static void compact_unreferenced_arrays(struct Parser *parser, struct Value *value) {
    size_t read_index;
    size_t write_index = 0;

    for (read_index = 0; read_index < parser->array_count; read_index++) {
        struct ArrayValue array = parser->arrays[read_index];
        int preserve_returned = value != NULL && value->kind == VALUE_ARRAY && value->array_id == array.id;
        int preserve_binding = binding_references_array(parser, array.id);
        int preserve_root = parser_roots_reference_array(parser, array.id);
        int preserve_under_construction = array.under_construction;

        if (preserve_returned || preserve_binding || preserve_root || preserve_under_construction) {
            if (preserve_returned) {
                value->array_index = write_index;
            }
            remap_binding_array_indices(parser, array.id, write_index);
            remap_parser_root_array_indices(parser, array.id, write_index);
            parser->arrays[write_index] = array;
            write_index++;
        }
    }
    parser->array_count = write_index;
}

static void compact_arrays_after_scope_pop(struct Parser *parser, struct Value *value) {
    size_t read_index;
    size_t write_index = 0;
    size_t parent_scope_depth = parser->scope_depth > 0 ? parser->scope_depth - 1 : 0;

    for (read_index = 0; read_index < parser->array_count; read_index++) {
        struct ArrayValue array = parser->arrays[read_index];
        int preserve_returned = value != NULL && value->kind == VALUE_ARRAY && value->array_id == array.id;
        int preserve_binding = binding_references_array(parser, array.id);
        int preserve_root = parser_roots_reference_array(parser, array.id);
        int preserve_under_construction = array.under_construction;

        if (array.scope_depth != parser->scope_depth || preserve_returned || preserve_binding || preserve_root || preserve_under_construction) {
            if (array.scope_depth == parser->scope_depth && (preserve_returned || preserve_binding || preserve_root)) {
                array.scope_depth = parent_scope_depth;
            }
            if (preserve_returned) {
                value->array_index = write_index;
            }
            remap_binding_array_indices(parser, array.id, write_index);
            remap_parser_root_array_indices(parser, array.id, write_index);
            parser->arrays[write_index] = array;
            write_index++;
        }
    }
    parser->array_count = write_index;
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
    compact_arrays_after_scope_pop(parser, NULL);
    if (parser->scope_depth > 0) {
        parser->scope_depth--;
    }
}

static void pop_scope_preserving_value(struct Parser *parser, struct Value *value) {
    while (parser->binding_count > 0 &&
           parser->bindings[parser->binding_count - 1].scope_depth == parser->scope_depth) {
        parser->binding_count--;
    }
    while (parser->function_count > 0 &&
           parser->functions[parser->function_count - 1].scope_depth == parser->scope_depth) {
        parser->function_count--;
    }
    compact_arrays_after_scope_pop(parser, value);
    if (parser->scope_depth > 0) {
        parser->scope_depth--;
    }
}

static struct Value parse_expression(struct Parser *parser);
static struct Value parse_statement_sequence(struct Parser *parser, char terminator);
static int skip_expression_operand(struct Parser *parser);

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
    pop_scope_preserving_value(parser, &value);
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

static int parse_match_arm_pattern(struct Parser *parser, long *out_pattern, int *out_is_default) {
    char *end = NULL;

    skip_spaces(parser);
    *out_is_default = 0;
    if (*parser->cursor == '_') {
        parser->cursor++;
        *out_is_default = 1;
    } else if (isdigit((unsigned char)*parser->cursor)) {
        *out_pattern = strtol(parser->cursor, &end, 10);
        parser->cursor = end;
    } else {
        parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
        return 0;
    }

    skip_spaces(parser);
    if (parser->cursor[0] != '=' || parser->cursor[1] != '>') {
        parser->status = RUSTIC_ERR_EXPECTED_EQUALS;
        return 0;
    }
    parser->cursor += 2;
    return 1;
}

static struct Value parse_match_expression(struct Parser *parser) {
    struct Value scrutinee_value;
    struct Value value = integer_value(0);
    long scrutinee;
    long pattern = 0;
    int is_default = 0;
    int matched = 0;

    parser->cursor += 5;
    scrutinee_value = parse_expression(parser);
    if (parser->status != RUSTIC_OK || !value_as_integer(parser, scrutinee_value, &scrutinee)) {
        return integer_value(0);
    }

    skip_spaces(parser);
    if (*parser->cursor != '{') {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
        return integer_value(0);
    }
    parser->cursor++;

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (*parser->cursor == '}') {
            parser->cursor++;
            if (!matched) {
                parser->status = RUSTIC_ERR_NO_MATCHING_MATCH_ARM;
                return integer_value(0);
            }
            return value;
        }

        if (!parse_match_arm_pattern(parser, &pattern, &is_default)) {
            return integer_value(0);
        }

        if (!matched && (is_default || pattern == scrutinee)) {
            value = parse_expression(parser);
            if (parser->status != RUSTIC_OK) {
                return integer_value(0);
            }
            matched = 1;
        } else if (!skip_expression_operand(parser)) {
            return integer_value(0);
        }

        skip_spaces(parser);
        if (parser->loop_control != LOOP_CONTROL_NONE) {
            while (*parser->cursor != '\0' && *parser->cursor != '}') {
                parser->cursor++;
            }
        }
        if (*parser->cursor == ',') {
            parser->cursor++;
            continue;
        }
        if (*parser->cursor == '}') {
            continue;
        }
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
        return integer_value(0);
    }

    return value;
}

static struct Value parse_while_statement(struct Parser *parser) {
    const char *condition_start;
    long condition;
    struct Value condition_value;
    size_t condition_array_count;
    struct Value value = integer_value(0);

    parser->cursor += 5;
    condition_start = parser->cursor;
    while (parser->status == RUSTIC_OK) {
        parser->cursor = condition_start;
        condition_array_count = parser->array_count;
        condition_value = parse_expression(parser);
        if (parser->status != RUSTIC_OK || !value_as_integer(parser, condition_value, &condition)) {
            parser->array_count = condition_array_count;
            return integer_value(0);
        }
        parser->array_count = condition_array_count;

        if (condition == 0) {
            if (!skip_block(parser)) {
                return integer_value(0);
            }
            return value;
        }

        parser->loop_depth++;
        value = parse_block_expression(parser);
        parser->loop_depth--;
        if (parser->status != RUSTIC_OK) {
            return integer_value(0);
        }
        if (parser->loop_control == LOOP_CONTROL_BREAK) {
            parser->loop_control = LOOP_CONTROL_NONE;
            return value;
        }
        if (parser->loop_control == LOOP_CONTROL_CONTINUE) {
            parser->loop_control = LOOP_CONTROL_NONE;
        }
    }

    return value;
}

static struct Value parse_index_postfix(struct Parser *parser, struct Value value) {
    struct ArrayValue *array;
    struct Value index_value;
    long index;

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (*parser->cursor != '[') {
            return value;
        }
        parser->cursor++;
        index_value = parse_expression(parser);
        if (parser->status != RUSTIC_OK || !value_as_integer(parser, index_value, &index)) {
            return integer_value(0);
        }
        skip_spaces(parser);
        if (*parser->cursor != ']') {
            parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACKET;
            return integer_value(0);
        }
        parser->cursor++;

        array = array_from_value(parser, value);
        if (array == NULL || index < 0 || (size_t)index >= array->element_count) {
            parser->status = RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS;
            return integer_value(0);
        }
        value = integer_value(array->elements[index]);
    }

    return value;
}

static struct Value parse_array_literal(struct Parser *parser) {
    struct ArrayValue *array;
    struct Value element_value;
    long element;
    size_t array_index;
    size_t array_id;

    if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
        parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
        return integer_value(0);
    }

    array_index = parser->array_count;
    array = &parser->arrays[array_index];
    array->element_count = 0;
    array->scope_depth = parser->scope_depth;
    array->id = parser->next_array_id;
    array->under_construction = 1;
    array_id = array->id;
    parser->next_array_id++;
    parser->array_count++;
    parser->cursor++;

    skip_spaces(parser);
    if (*parser->cursor != ']') {
        while (parser->status == RUSTIC_OK) {
            if (array->element_count >= RUSTIC_MAX_ARRAY_ELEMENTS) {
                parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                return integer_value(0);
            }
            element_value = parse_expression(parser);
            array = array_by_id(parser, array_id, &array_index);
            if (array == NULL) {
                parser->status = RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS;
                return integer_value(0);
            }
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, element_value, &element)) {
                return integer_value(0);
            }
            array->elements[array->element_count] = element;
            array->element_count++;
            skip_spaces(parser);
            if (*parser->cursor != ',') {
                break;
            }
            parser->cursor++;
            skip_spaces(parser);
        }
    }

    if (*parser->cursor != ']') {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACKET;
        return integer_value(0);
    }
    parser->cursor++;
    array = array_by_id(parser, array_id, &array_index);
    if (array == NULL) {
        parser->status = RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS;
        return integer_value(0);
    }
    array->under_construction = 0;
    return array_value(array_index, array->id);
}

static struct Value call_unary_function(struct Parser *parser, struct Function *function, long argument) {
    const char *call_return;
    size_t saved_loop_depth;
    enum LoopControl saved_loop_control;
    struct Value value;

    if (function->parameter_count != 1) {
        parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
        return integer_value(0);
    }

    call_return = parser->cursor;
    parser->cursor = function->body_start;
    saved_loop_depth = parser->loop_depth;
    saved_loop_control = parser->loop_control;
    parser->loop_depth = 0;
    parser->loop_control = LOOP_CONTROL_NONE;
    push_scope(parser);
    add_binding(parser, function->parameters[0], integer_value(argument));
    if (parser->status != RUSTIC_OK) {
        pop_scope(parser);
        parser->cursor = call_return;
        parser->loop_depth = saved_loop_depth;
        parser->loop_control = saved_loop_control;
        return integer_value(0);
    }

    value = parse_statement_sequence(parser, '}');
    if (parser->status != RUSTIC_OK) {
        pop_scope(parser);
        parser->cursor = call_return;
        parser->loop_depth = saved_loop_depth;
        parser->loop_control = saved_loop_control;
        return integer_value(0);
    }
    skip_spaces(parser);
    if (parser->cursor != function->body_end) {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
        pop_scope(parser);
        parser->cursor = call_return;
        parser->loop_depth = saved_loop_depth;
        parser->loop_control = saved_loop_control;
        return integer_value(0);
    }
    pop_scope_preserving_value(parser, &value);
    parser->cursor = call_return;
    parser->loop_depth = saved_loop_depth;
    parser->loop_control = saved_loop_control;
    return value;
}

static struct Value call_binary_function(struct Parser *parser, struct Function *function, long left, long right) {
    const char *call_return;
    size_t saved_loop_depth;
    enum LoopControl saved_loop_control;
    struct Value value;

    if (function->parameter_count != 2) {
        parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
        return integer_value(0);
    }

    call_return = parser->cursor;
    parser->cursor = function->body_start;
    saved_loop_depth = parser->loop_depth;
    saved_loop_control = parser->loop_control;
    parser->loop_depth = 0;
    parser->loop_control = LOOP_CONTROL_NONE;
    push_scope(parser);
    add_binding(parser, function->parameters[0], integer_value(left));
    add_binding(parser, function->parameters[1], integer_value(right));
    if (parser->status != RUSTIC_OK) {
        pop_scope(parser);
        parser->cursor = call_return;
        parser->loop_depth = saved_loop_depth;
        parser->loop_control = saved_loop_control;
        return integer_value(0);
    }

    value = parse_statement_sequence(parser, '}');
    if (parser->status != RUSTIC_OK) {
        pop_scope(parser);
        parser->cursor = call_return;
        parser->loop_depth = saved_loop_depth;
        parser->loop_control = saved_loop_control;
        return integer_value(0);
    }
    skip_spaces(parser);
    if (parser->cursor != function->body_end) {
        parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
        pop_scope(parser);
        parser->cursor = call_return;
        parser->loop_depth = saved_loop_depth;
        parser->loop_control = saved_loop_control;
        return integer_value(0);
    }
    pop_scope_preserving_value(parser, &value);
    parser->cursor = call_return;
    parser->loop_depth = saved_loop_depth;
    parser->loop_control = saved_loop_control;
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
    size_t saved_loop_depth;
    enum LoopControl saved_loop_control;

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
        return parse_index_postfix(parser, parse_block_expression(parser));
    }

    if (cursor_starts_keyword(parser, "if")) {
        return parse_index_postfix(parser, parse_if_expression(parser));
    }

    if (cursor_starts_keyword(parser, "match")) {
        return parse_index_postfix(parser, parse_match_expression(parser));
    }

    if (*parser->cursor == '[') {
        return parse_index_postfix(parser, parse_array_literal(parser));
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
        return parse_index_postfix(parser, value);
    }

    if (isdigit((unsigned char)*parser->cursor)) {
        integer = strtol(parser->cursor, &end, 10);
        parser->cursor = end;
        return parse_index_postfix(parser, integer_value(integer));
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
                    {
                        struct Value *saved_array_roots = parser->array_roots;
                        size_t saved_array_root_count = parser->array_root_count;
                        struct Value combined_roots[RUSTIC_MAX_ARRAY_ROOTS];
                        size_t root_index;
                        if (saved_array_root_count + argument_count > RUSTIC_MAX_ARRAY_ROOTS) {
                            parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                            return integer_value(0);
                        }
                        for (root_index = 0; root_index < saved_array_root_count; root_index++) {
                            combined_roots[root_index] = saved_array_roots[root_index];
                        }
                        for (root_index = 0; root_index < argument_count; root_index++) {
                            combined_roots[saved_array_root_count + root_index] = arguments[root_index];
                        }
                        parser->array_roots = combined_roots;
                        parser->array_root_count = saved_array_root_count + argument_count;
                        arguments[argument_count] = parse_expression(parser);
                        for (root_index = 0; root_index < saved_array_root_count; root_index++) {
                            saved_array_roots[root_index] = combined_roots[root_index];
                        }
                        for (root_index = 0; root_index < argument_count; root_index++) {
                            arguments[root_index] = combined_roots[saved_array_root_count + root_index];
                        }
                        parser->array_roots = saved_array_roots;
                        parser->array_root_count = saved_array_root_count;
                    }
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

            if (strcmp(name, "len") == 0) {
                struct ArrayValue *array;

                if (argument_count != 1) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                return parse_index_postfix(parser, integer_value((long)array->element_count));
            }

            if (strcmp(name, "range") == 0) {
                struct ArrayValue *array;
                long length;
                size_t element_index;

                if (argument_count != 1) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[0], &length)) {
                    return integer_value(0);
                }
                if (length < 0) {
                    parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
                    return integer_value(0);
                }
                if ((size_t)length > RUSTIC_MAX_ARRAY_ELEMENTS || parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }

                array = &parser->arrays[parser->array_count];
                array->element_count = (size_t)length;
                array->scope_depth = parser->scope_depth;
                array->id = parser->next_array_id;
                array->under_construction = 0;
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    array->elements[element_index] = (long)element_index;
                }
                value = array_value(parser->array_count, array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (strcmp(name, "reverse") == 0 || strcmp(name, "take") == 0 || strcmp(name, "drop") == 0 || strcmp(name, "sort") == 0 || strcmp(name, "dedup") == 0 || strcmp(name, "window_sum") == 0 || strcmp(name, "moving_average_sum") == 0 || strcmp(name, "chunk_count") == 0 || strcmp(name, "chunk_sum") == 0 || strcmp(name, "rotate") == 0 || strcmp(name, "rotate_right") == 0 || strcmp(name, "prefix_sum") == 0 || strcmp(name, "adjacent_diff") == 0) {
                struct ArrayValue *source_array;
                struct ArrayValue *result_array;
                long source_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long result_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long slice_count = 0;
                long window_size = 0;
                long chunk_size = 0;
                long rotation_count = 0;
                size_t source_count;
                size_t result_count;
                size_t slice_start = 0;
                size_t element_index;
                int taking = strcmp(name, "take") == 0;
                int dropping = strcmp(name, "drop") == 0;
                int sorting = strcmp(name, "sort") == 0;
                int deduplicating = strcmp(name, "dedup") == 0;
                int windowing = strcmp(name, "window_sum") == 0;
                int moving_averaging = strcmp(name, "moving_average_sum") == 0;
                int chunking = strcmp(name, "chunk_count") == 0;
                int chunk_summing = strcmp(name, "chunk_sum") == 0;
                int rotating = strcmp(name, "rotate") == 0;
                int rotating_right = strcmp(name, "rotate_right") == 0;
                int prefixing = strcmp(name, "prefix_sum") == 0;
                int differencing = strcmp(name, "adjacent_diff") == 0;

                if (argument_count != ((taking || dropping || windowing || moving_averaging || chunking || chunk_summing || rotating || rotating_right) ? 2 : 1)) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                source_array = array_from_value(parser, arguments[0]);
                if (source_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (taking || dropping) {
                    if (!value_as_integer(parser, arguments[1], &slice_count)) {
                        return integer_value(0);
                    }
                    if (slice_count < 0) {
                        parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
                        return integer_value(0);
                    }
                }
                if (windowing || moving_averaging) {
                    if (!value_as_integer(parser, arguments[1], &window_size)) {
                        return integer_value(0);
                    }
                    if (window_size <= 0) {
                        parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
                        return integer_value(0);
                    }
                }
                if (chunking || chunk_summing) {
                    if (!value_as_integer(parser, arguments[1], &chunk_size)) {
                        return integer_value(0);
                    }
                    if (chunk_size <= 0) {
                        parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
                        return integer_value(0);
                    }
                }
                if (rotating || rotating_right) {
                    if (!value_as_integer(parser, arguments[1], &rotation_count)) {
                        return integer_value(0);
                    }
                    if (rotation_count < 0) {
                        parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
                        return integer_value(0);
                    }
                }

                source_count = source_array->element_count;
                for (element_index = 0; element_index < source_count; element_index++) {
                    source_elements[element_index] = source_array->elements[element_index];
                }
                if (taking && (size_t)slice_count < source_count) {
                    result_count = (size_t)slice_count;
                } else if (dropping) {
                    slice_start = (size_t)slice_count < source_count ? (size_t)slice_count : source_count;
                    result_count = source_count - slice_start;
                } else if (windowing || moving_averaging) {
                    result_count = (size_t)window_size <= source_count ? source_count - (size_t)window_size + 1 : 0;
                } else if (chunk_summing) {
                    result_count = source_count > 0 ? (source_count + (size_t)chunk_size - 1) / (size_t)chunk_size : 0;
                } else {
                    result_count = source_count;
                }

                if (chunking) {
                    long chunks = 0;
                    if (source_count > 0) {
                        chunks = (long)((source_count + (size_t)chunk_size - 1) / (size_t)chunk_size);
                    }
                    return parse_index_postfix(parser, integer_value(chunks));
                }

                if (sorting) {
                    size_t scan_index;
                    for (element_index = 0; element_index < source_count; element_index++) {
                        result_elements[element_index] = source_elements[element_index];
                    }
                    for (element_index = 1; element_index < source_count; element_index++) {
                        long current = result_elements[element_index];
                        scan_index = element_index;
                        while (scan_index > 0 && result_elements[scan_index - 1] > current) {
                            result_elements[scan_index] = result_elements[scan_index - 1];
                            scan_index--;
                        }
                        result_elements[scan_index] = current;
                    }
                } else if (deduplicating) {
                    size_t candidate_index;
                    result_count = 0;
                    for (element_index = 0; element_index < source_count; element_index++) {
                        int seen = 0;
                        for (candidate_index = 0; candidate_index < result_count; candidate_index++) {
                            if (result_elements[candidate_index] == source_elements[element_index]) {
                                seen = 1;
                                break;
                            }
                        }
                        if (!seen) {
                            result_elements[result_count] = source_elements[element_index];
                            result_count++;
                        }
                    }
                } else if (windowing || moving_averaging) {
                    size_t window_index;
                    size_t offset;
                    for (window_index = 0; window_index < result_count; window_index++) {
                        long total = 0;
                        for (offset = 0; offset < (size_t)window_size; offset++) {
                            total += source_elements[window_index + offset];
                        }
                        result_elements[window_index] = moving_averaging ? total / window_size : total;
                    }
                } else if (chunk_summing) {
                    size_t chunk_index;
                    size_t offset;
                    for (chunk_index = 0; chunk_index < result_count; chunk_index++) {
                        long total = 0;
                        size_t chunk_start = chunk_index * (size_t)chunk_size;
                        size_t chunk_end = chunk_start + (size_t)chunk_size;
                        if (chunk_end > source_count) {
                            chunk_end = source_count;
                        }
                        for (offset = chunk_start; offset < chunk_end; offset++) {
                            total += source_elements[offset];
                        }
                        result_elements[chunk_index] = total;
                    }
                } else if (rotating && source_count > 0) {
                    size_t offset = (size_t)rotation_count % source_count;
                    for (element_index = 0; element_index < result_count; element_index++) {
                        result_elements[element_index] = source_elements[(element_index + offset) % source_count];
                    }
                } else if (rotating_right && source_count > 0) {
                    size_t offset = (size_t)rotation_count % source_count;
                    for (element_index = 0; element_index < result_count; element_index++) {
                        result_elements[element_index] = source_elements[(element_index + source_count - offset) % source_count];
                    }
                } else if (prefixing) {
                    long total = 0;
                    for (element_index = 0; element_index < result_count; element_index++) {
                        total += source_elements[element_index];
                        result_elements[element_index] = total;
                    }
                } else if (differencing) {
                    for (element_index = 0; element_index < result_count; element_index++) {
                        if (element_index == 0) {
                            result_elements[element_index] = source_elements[element_index];
                        } else {
                            result_elements[element_index] = source_elements[element_index] - source_elements[element_index - 1];
                        }
                    }
                }

                compact_unreferenced_arrays(parser, &arguments[0]);
                if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }
                result_array = &parser->arrays[parser->array_count];
                result_array->element_count = result_count;
                result_array->scope_depth = parser->scope_depth;
                result_array->id = parser->next_array_id;
                result_array->under_construction = 0;
                for (element_index = 0; element_index < result_count; element_index++) {
                    if (taking || dropping) {
                        result_array->elements[element_index] = source_elements[slice_start + element_index];
                    } else if (sorting || deduplicating || windowing || moving_averaging || chunk_summing || rotating || rotating_right || prefixing || differencing) {
                        result_array->elements[element_index] = result_elements[element_index];
                    } else {
                        result_array->elements[element_index] = source_elements[source_count - element_index - 1];
                    }
                }
                value = array_value(parser->array_count, result_array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (strcmp(name, "repeat") == 0) {
                struct ArrayValue *array;
                long repeated_value;
                long repeat_count;
                size_t element_index;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[0], &repeated_value)) {
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &repeat_count)) {
                    return integer_value(0);
                }
                if (repeat_count < 0) {
                    parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
                    return integer_value(0);
                }
                compact_unreferenced_arrays(parser, NULL);
                if ((size_t)repeat_count > RUSTIC_MAX_ARRAY_ELEMENTS || parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }

                array = &parser->arrays[parser->array_count];
                array->element_count = (size_t)repeat_count;
                array->scope_depth = parser->scope_depth;
                array->id = parser->next_array_id;
                array->under_construction = 0;
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    array->elements[element_index] = repeated_value;
                }
                value = array_value(parser->array_count, array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (strcmp(name, "concat") == 0) {
                struct ArrayValue *left_array;
                struct ArrayValue *right_array;
                struct ArrayValue *result_array;
                long result_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                size_t left_count;
                size_t right_count;
                size_t result_count;
                size_t element_index;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                left_array = array_from_value(parser, arguments[0]);
                if (left_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                right_array = array_from_value(parser, arguments[1]);
                if (right_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                left_count = left_array->element_count;
                right_count = right_array->element_count;
                result_count = left_count + right_count;
                if (result_count > RUSTIC_MAX_ARRAY_ELEMENTS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }
                for (element_index = 0; element_index < left_count; element_index++) {
                    result_elements[element_index] = left_array->elements[element_index];
                }
                for (element_index = 0; element_index < right_count; element_index++) {
                    result_elements[left_count + element_index] = right_array->elements[element_index];
                }

                compact_unreferenced_arrays(parser, NULL);
                if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }
                result_array = &parser->arrays[parser->array_count];
                result_array->element_count = result_count;
                result_array->scope_depth = parser->scope_depth;
                result_array->id = parser->next_array_id;
                result_array->under_construction = 0;
                for (element_index = 0; element_index < result_count; element_index++) {
                    result_array->elements[element_index] = result_elements[element_index];
                }
                value = array_value(parser->array_count, result_array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (strcmp(name, "partition_count") == 0) {
                struct ArrayValue *source_array;
                struct Function *predicate;
                long source_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                size_t source_count;
                size_t element_index;
                long matched_count = 0;
                long predicate_result;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                source_array = array_from_value(parser, arguments[0]);
                if (source_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                predicate = function_from_value(parser, arguments[1]);
                if (predicate == NULL) {
                    parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
                    return integer_value(0);
                }
                if (predicate->parameter_count != 1) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }

                source_count = source_array->element_count;
                for (element_index = 0; element_index < source_count; element_index++) {
                    source_elements[element_index] = source_array->elements[element_index];
                }
                for (element_index = 0; element_index < source_count; element_index++) {
                    struct Value predicate_value = call_unary_function(parser, predicate, source_elements[element_index]);
                    if (parser->status != RUSTIC_OK || !value_as_integer(parser, predicate_value, &predicate_result)) {
                        return integer_value(0);
                    }
                    if (predicate_result != 0) {
                        matched_count++;
                    }
                }
                compact_unreferenced_arrays(parser, &arguments[0]);
                return parse_index_postfix(parser, integer_value(matched_count));
            }

            if (strcmp(name, "map") == 0 || strcmp(name, "filter") == 0 || strcmp(name, "map_indexed") == 0 || strcmp(name, "filter_indexed") == 0) {
                struct ArrayValue *source_array;
                struct ArrayValue *result_array;
                struct Function *transform;
                long source_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long result_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                size_t source_count;
                size_t result_count = 0;
                size_t element_index;
                long transformed;
                int filtering = strcmp(name, "filter") == 0 || strcmp(name, "filter_indexed") == 0;
                int indexed = strcmp(name, "map_indexed") == 0 || strcmp(name, "filter_indexed") == 0;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                source_array = array_from_value(parser, arguments[0]);
                if (source_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                transform = function_from_value(parser, arguments[1]);
                if (transform == NULL) {
                    parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
                    return integer_value(0);
                }
                if (transform->parameter_count != (indexed ? 2u : 1u)) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }

                source_count = source_array->element_count;
                for (element_index = 0; element_index < source_count; element_index++) {
                    source_elements[element_index] = source_array->elements[element_index];
                }

                for (element_index = 0; element_index < source_count; element_index++) {
                    struct Value transformed_value;
                    if (indexed) {
                        transformed_value = call_binary_function(parser, transform, (long)element_index, source_elements[element_index]);
                    } else {
                        transformed_value = call_unary_function(parser, transform, source_elements[element_index]);
                    }
                    if (parser->status != RUSTIC_OK || !value_as_integer(parser, transformed_value, &transformed)) {
                        return integer_value(0);
                    }
                    if (filtering) {
                        if (transformed != 0) {
                            result_elements[result_count] = source_elements[element_index];
                            result_count++;
                        }
                    } else {
                        result_elements[result_count] = transformed;
                        result_count++;
                    }
                }

                compact_unreferenced_arrays(parser, &arguments[0]);
                if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }
                result_array = &parser->arrays[parser->array_count];
                result_array->element_count = result_count;
                result_array->scope_depth = parser->scope_depth;
                result_array->id = parser->next_array_id;
                result_array->under_construction = 0;
                for (element_index = 0; element_index < result_count; element_index++) {
                    result_array->elements[element_index] = result_elements[element_index];
                }
                value = array_value(parser->array_count, result_array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (strcmp(name, "zip_with") == 0) {
                struct ArrayValue *left_array;
                struct ArrayValue *right_array;
                struct ArrayValue *result_array;
                struct Function *zipper;
                long left_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long right_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long result_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                size_t left_count;
                size_t right_count;
                size_t result_count;
                size_t element_index;
                long combined;

                if (argument_count != 3) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                left_array = array_from_value(parser, arguments[0]);
                if (left_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                right_array = array_from_value(parser, arguments[1]);
                if (right_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                zipper = function_from_value(parser, arguments[2]);
                if (zipper == NULL) {
                    parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
                    return integer_value(0);
                }
                if (zipper->parameter_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }

                left_count = left_array->element_count;
                right_count = right_array->element_count;
                result_count = left_count < right_count ? left_count : right_count;
                for (element_index = 0; element_index < left_count; element_index++) {
                    left_elements[element_index] = left_array->elements[element_index];
                }
                for (element_index = 0; element_index < right_count; element_index++) {
                    right_elements[element_index] = right_array->elements[element_index];
                }

                for (element_index = 0; element_index < result_count; element_index++) {
                    struct Value combined_value = call_binary_function(parser, zipper, left_elements[element_index], right_elements[element_index]);
                    if (parser->status != RUSTIC_OK || !value_as_integer(parser, combined_value, &combined)) {
                        return integer_value(0);
                    }
                    result_elements[element_index] = combined;
                }

                compact_unreferenced_arrays(parser, NULL);
                if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }
                result_array = &parser->arrays[parser->array_count];
                result_array->element_count = result_count;
                result_array->scope_depth = parser->scope_depth;
                result_array->id = parser->next_array_id;
                result_array->under_construction = 0;
                for (element_index = 0; element_index < result_count; element_index++) {
                    result_array->elements[element_index] = result_elements[element_index];
                }
                value = array_value(parser->array_count, result_array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (strcmp(name, "fold") == 0) {
                struct ArrayValue *source_array;
                struct Function *reducer;
                long source_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                size_t source_count;
                size_t element_index;
                long accumulator;

                if (argument_count != 3) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                source_array = array_from_value(parser, arguments[0]);
                if (source_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &accumulator)) {
                    return integer_value(0);
                }
                reducer = function_from_value(parser, arguments[2]);
                if (reducer == NULL) {
                    parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
                    return integer_value(0);
                }
                if (reducer->parameter_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }

                source_count = source_array->element_count;
                for (element_index = 0; element_index < source_count; element_index++) {
                    source_elements[element_index] = source_array->elements[element_index];
                }

                for (element_index = 0; element_index < source_count; element_index++) {
                    struct Value folded_value = call_binary_function(parser, reducer, accumulator, source_elements[element_index]);
                    if (parser->status != RUSTIC_OK || !value_as_integer(parser, folded_value, &accumulator)) {
                        return integer_value(0);
                    }
                }
                compact_unreferenced_arrays(parser, &arguments[0]);
                return parse_index_postfix(parser, integer_value(accumulator));
            }

            if (strcmp(name, "sum") == 0) {
                struct ArrayValue *array;
                long total = 0;
                size_t element_index;

                if (argument_count != 1) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    total += array->elements[element_index];
                }
                return parse_index_postfix(parser, integer_value(total));
            }

            if (strcmp(name, "count") == 0) {
                struct ArrayValue *array;
                long target;
                long matches = 0;
                size_t element_index;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &target)) {
                    return integer_value(0);
                }
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    if (array->elements[element_index] == target) {
                        matches++;
                    }
                }
                return parse_index_postfix(parser, integer_value(matches));
            }

            if (strcmp(name, "find") == 0) {
                struct ArrayValue *array;
                long target;
                long found_index = -1;
                size_t element_index;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &target)) {
                    return integer_value(0);
                }
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    if (array->elements[element_index] == target) {
                        found_index = (long)element_index;
                        break;
                    }
                }
                return parse_index_postfix(parser, integer_value(found_index));
            }

            if (strcmp(name, "contains_any") == 0 || strcmp(name, "equals") == 0 || strcmp(name, "starts_with") == 0 || strcmp(name, "intersection_count") == 0 || strcmp(name, "difference") == 0) {
                struct ArrayValue *left_array;
                struct ArrayValue *right_array;
                struct ArrayValue *result_array;
                long left_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long right_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long result_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long matched;
                size_t left_count;
                size_t right_count;
                size_t result_count = 0;
                size_t left_index;
                size_t right_index;
                int checking_any = strcmp(name, "contains_any") == 0;
                int checking_equals = strcmp(name, "equals") == 0;
                int counting_intersection = strcmp(name, "intersection_count") == 0;
                int building_difference = strcmp(name, "difference") == 0;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                left_array = array_from_value(parser, arguments[0]);
                if (left_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                right_array = array_from_value(parser, arguments[1]);
                if (right_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }

                left_count = left_array->element_count;
                right_count = right_array->element_count;
                for (left_index = 0; left_index < left_count; left_index++) {
                    left_elements[left_index] = left_array->elements[left_index];
                }
                for (right_index = 0; right_index < right_count; right_index++) {
                    right_elements[right_index] = right_array->elements[right_index];
                }

                if (checking_any) {
                    matched = 0;
                    for (left_index = 0; left_index < left_count; left_index++) {
                        for (right_index = 0; right_index < right_count; right_index++) {
                            if (left_elements[left_index] == right_elements[right_index]) {
                                matched = 1;
                                break;
                            }
                        }
                        if (matched) {
                            break;
                        }
                    }
                } else if (counting_intersection) {
                    matched = 0;
                    for (left_index = 0; left_index < left_count; left_index++) {
                        int seen_left = 0;
                        int seen_right = 0;
                        size_t scan_index;
                        for (scan_index = 0; scan_index < left_index; scan_index++) {
                            if (left_elements[scan_index] == left_elements[left_index]) {
                                seen_left = 1;
                                break;
                            }
                        }
                        if (seen_left) {
                            continue;
                        }
                        for (right_index = 0; right_index < right_count; right_index++) {
                            if (left_elements[left_index] == right_elements[right_index]) {
                                seen_right = 1;
                                break;
                            }
                        }
                        if (seen_right) {
                            matched++;
                        }
                    }
                } else if (building_difference) {
                    for (left_index = 0; left_index < left_count; left_index++) {
                        int found_in_right = 0;
                        for (right_index = 0; right_index < right_count; right_index++) {
                            if (left_elements[left_index] == right_elements[right_index]) {
                                found_in_right = 1;
                                break;
                            }
                        }
                        if (!found_in_right) {
                            result_elements[result_count] = left_elements[left_index];
                            result_count++;
                        }
                    }
                    compact_unreferenced_arrays(parser, NULL);
                    if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                        parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                        return integer_value(0);
                    }
                    result_array = &parser->arrays[parser->array_count];
                    result_array->element_count = result_count;
                    result_array->scope_depth = parser->scope_depth;
                    result_array->id = parser->next_array_id;
                    result_array->under_construction = 0;
                    for (left_index = 0; left_index < result_count; left_index++) {
                        result_array->elements[left_index] = result_elements[left_index];
                    }
                    value = array_value(parser->array_count, result_array->id);
                    parser->array_count++;
                    parser->next_array_id++;
                    return parse_index_postfix(parser, value);
                } else {
                    size_t required_count = checking_equals ? left_count : right_count;
                    matched = 1;
                    if (checking_equals && left_count != right_count) {
                        matched = 0;
                    } else if (required_count > left_count) {
                        matched = 0;
                    } else {
                        for (left_index = 0; left_index < required_count; left_index++) {
                            if (left_elements[left_index] != right_elements[left_index]) {
                                matched = 0;
                                break;
                            }
                        }
                    }
                }
                compact_unreferenced_arrays(parser, NULL);
                return parse_index_postfix(parser, integer_value(matched));
            }

            if (strcmp(name, "any") == 0 || strcmp(name, "all") == 0) {
                struct ArrayValue *array;
                long target;
                long matched;
                size_t element_index;
                int require_all = strcmp(name, "all") == 0;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &target)) {
                    return integer_value(0);
                }
                matched = require_all ? 1 : 0;
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    if (array->elements[element_index] == target) {
                        if (!require_all) {
                            matched = 1;
                            break;
                        }
                    } else if (require_all) {
                        matched = 0;
                        break;
                    }
                }
                return parse_index_postfix(parser, integer_value(matched));
            }

            if (strcmp(name, "frequency_score") == 0) {
                struct ArrayValue *array;
                long target;
                long matched = 0;
                size_t element_index;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &target)) {
                    return integer_value(0);
                }
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    if (array->elements[element_index] == target) {
                        matched++;
                    }
                }
                compact_unreferenced_arrays(parser, &arguments[0]);
                return parse_index_postfix(parser, integer_value(matched));
            }

            if (strcmp(name, "histogram_pairs_score") == 0) {
                struct ArrayValue *values;
                struct ArrayValue *counts;
                long score = 0;
                size_t element_index;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                values = array_from_value(parser, arguments[0]);
                if (values == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                counts = array_from_value(parser, arguments[1]);
                if (counts == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (values->element_count != counts->element_count) {
                    parser->status = RUSTIC_ERR_ARRAY_LENGTH_MISMATCH;
                    return integer_value(0);
                }
                for (element_index = 0; element_index < values->element_count; element_index++) {
                    score += values->elements[element_index] * counts->elements[element_index];
                }
                compact_unreferenced_arrays(parser, NULL);
                return parse_index_postfix(parser, integer_value(score));
            }

            if (strcmp(name, "threshold_count") == 0 || strcmp(name, "threshold_all") == 0 || strcmp(name, "outlier_count") == 0 || strcmp(name, "outlier_score") == 0) {
                struct ArrayValue *array;
                long lower_bound;
                long upper_bound;
                long matched = 0;
                size_t element_index;
                int requiring_all = strcmp(name, "threshold_all") == 0;
                int counting_outliers = strcmp(name, "outlier_count") == 0;
                int scoring_outliers = strcmp(name, "outlier_score") == 0;

                if (argument_count != 3) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &lower_bound)) {
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[2], &upper_bound)) {
                    return integer_value(0);
                }
                matched = requiring_all ? 1 : 0;
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    int in_range = array->elements[element_index] >= lower_bound && array->elements[element_index] <= upper_bound;
                    if (requiring_all) {
                        if (!in_range) {
                            matched = 0;
                            break;
                        }
                    } else if (counting_outliers) {
                        if (!in_range) {
                            matched++;
                        }
                    } else if (scoring_outliers) {
                        if (array->elements[element_index] < lower_bound) {
                            matched += lower_bound - array->elements[element_index];
                        } else if (array->elements[element_index] > upper_bound) {
                            matched += array->elements[element_index] - upper_bound;
                        }
                    } else if (in_range) {
                        matched++;
                    }
                }
                compact_unreferenced_arrays(parser, &arguments[0]);
                return parse_index_postfix(parser, integer_value(matched));
            }

            if (strcmp(name, "threshold_window_count") == 0) {
                struct ArrayValue *array;
                long lower_bound;
                long upper_bound;
                long window_size;
                long matched = 0;
                size_t window_start;
                size_t offset;

                if (argument_count != 4) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &lower_bound)) {
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[2], &upper_bound)) {
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[3], &window_size)) {
                    return integer_value(0);
                }
                if (window_size <= 0) {
                    parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
                    return integer_value(0);
                }
                if ((size_t)window_size <= array->element_count) {
                    for (window_start = 0; window_start + (size_t)window_size <= array->element_count; window_start++) {
                        int window_in_range = 1;
                        for (offset = 0; offset < (size_t)window_size; offset++) {
                            long element = array->elements[window_start + offset];
                            if (element < lower_bound || element > upper_bound) {
                                window_in_range = 0;
                                break;
                            }
                        }
                        if (window_in_range) {
                            matched++;
                        }
                    }
                }
                compact_unreferenced_arrays(parser, &arguments[0]);
                return parse_index_postfix(parser, integer_value(matched));
            }

            if (strcmp(name, "threshold_run_count") == 0 || strcmp(name, "outlier_streak") == 0 || strcmp(name, "threshold_run_score") == 0 || strcmp(name, "outlier_run_count") == 0 || strcmp(name, "threshold_run_lengths") == 0 || strcmp(name, "outlier_run_lengths") == 0 || strcmp(name, "threshold_run_length_score") == 0 || strcmp(name, "outlier_run_length_score") == 0 || strcmp(name, "threshold_longest_run") == 0 || strcmp(name, "threshold_shortest_run") == 0 || strcmp(name, "outlier_shortest_run") == 0 || strcmp(name, "outlier_longest_run") == 0 || strcmp(name, "threshold_run_delta") == 0 || strcmp(name, "outlier_run_delta") == 0 || strcmp(name, "threshold_run_ratio_score") == 0 || strcmp(name, "outlier_run_ratio_score") == 0 || strcmp(name, "threshold_transition_count") == 0 || strcmp(name, "outlier_transition_count") == 0 || strcmp(name, "threshold_transition_score") == 0 || strcmp(name, "outlier_transition_score") == 0 || strcmp(name, "threshold_transition_density") == 0 || strcmp(name, "outlier_transition_density") == 0 || strcmp(name, "threshold_transition_balance") == 0 || strcmp(name, "outlier_transition_balance") == 0 || strcmp(name, "threshold_run_contrast") == 0 || strcmp(name, "outlier_run_contrast") == 0 || strcmp(name, "threshold_run_contrast_delta") == 0 || strcmp(name, "outlier_run_contrast_delta") == 0 || strcmp(name, "threshold_run_signal_score") == 0 || strcmp(name, "outlier_run_signal_score") == 0 || strcmp(name, "threshold_run_signal_density") == 0 || strcmp(name, "outlier_run_signal_density") == 0 || strcmp(name, "threshold_run_signal_density_delta") == 0 || strcmp(name, "outlier_run_signal_density_delta") == 0 || strcmp(name, "threshold_run_signal_density_ratio") == 0 || strcmp(name, "outlier_run_signal_density_ratio") == 0 || strcmp(name, "threshold_run_signal_density_gap") == 0 || strcmp(name, "outlier_run_signal_density_gap") == 0 || strcmp(name, "threshold_run_signal_density_band") == 0 || strcmp(name, "outlier_run_signal_density_band") == 0 || strcmp(name, "threshold_run_signal_density_band_ratio") == 0 || strcmp(name, "outlier_run_signal_density_band_ratio") == 0 || strcmp(name, "threshold_run_signal_density_band_gap") == 0 || strcmp(name, "outlier_run_signal_density_band_gap") == 0 || strcmp(name, "threshold_run_signal_density_band_gap_ratio") == 0 || strcmp(name, "outlier_run_signal_density_band_gap_ratio") == 0 || strcmp(name, "threshold_run_signal_density_band_span") == 0 || strcmp(name, "outlier_run_signal_density_band_span") == 0 || strcmp(name, "threshold_run_signal_density_band_span_ratio") == 0 || strcmp(name, "outlier_run_signal_density_band_span_ratio") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_ratio") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_ratio") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_ratio") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_ratio") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ratio") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ratio") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_delta") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_delta") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_count") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_count") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_drift") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_drift") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spread") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spread") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mass") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mass") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_load") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_load") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_flux") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_flux") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_wave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_wave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_peak") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_peak") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_edge") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_edge") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rim") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rim") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lip") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lip") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jaw") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jaw") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bite") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bite") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grip") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grip") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_hold") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_hold") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lock") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lock") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seal") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seal") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mark") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mark") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stamp") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stamp") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_press") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_press") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pin") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pin") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_snap") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_snap") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_clasp") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_clasp") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_latch") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_latch") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_hook") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_hook") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_link") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_link") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_chain") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_chain") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rope") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rope") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knot") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knot") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tie") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tie") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bow") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bow") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_arc") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_arc") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_guard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_guard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shield") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shield") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_wall") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_wall") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fort") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fort") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_keep") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_keep") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_core") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_core") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_root") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_root") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_crown") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_crown") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_crest") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_crest") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_plume") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_plume") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spire") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spire") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_flare") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_flare") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spark") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spark") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_torch") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_torch") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ember") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ember") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_glow") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_glow") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ash") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ash") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_blaze") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_blaze") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_flame") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_flame") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_smoke") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_smoke") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stone") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stone") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_forge") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_forge") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_anvil") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_anvil") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_metal") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_metal") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_iron") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_iron") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mold") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mold") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cast") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cast") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ore") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ore") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ingot") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_steel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_smelt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_alloy") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fuse") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ingot") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_steel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_smelt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_alloy") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fuse") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))))))) || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_brand") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_brand") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_halo") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_halo") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_arch") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_arch") == 0) {
                struct ArrayValue *array;
                long lower_bound;
                long upper_bound;
                long matched = 0;
                long current_streak = 0;
                long longest_run = 0;
                long shortest_run = 0;
                long run_lengths[RUSTIC_MAX_ARRAY_ELEMENTS];
                size_t run_count = 0;
                size_t element_index;
                int has_previous_range_state = 0;
                int previous_in_range = 0;
                int measuring_outlier_streak = strcmp(name, "outlier_streak") == 0 || strcmp(name, "outlier_longest_run") == 0;
                int measuring_outlier_runs = strcmp(name, "outlier_run_count") == 0;
                int measuring_threshold_longest = strcmp(name, "threshold_longest_run") == 0;
                int measuring_threshold_shortest = strcmp(name, "threshold_shortest_run") == 0;
                int measuring_outlier_shortest = strcmp(name, "outlier_shortest_run") == 0;
                int measuring_threshold_delta = strcmp(name, "threshold_run_delta") == 0;
                int measuring_outlier_delta = strcmp(name, "outlier_run_delta") == 0;
                int measuring_threshold_ratio = strcmp(name, "threshold_run_ratio_score") == 0;
                int measuring_outlier_ratio = strcmp(name, "outlier_run_ratio_score") == 0;
                int measuring_transition_count = strcmp(name, "threshold_transition_count") == 0 || strcmp(name, "outlier_transition_count") == 0;
                int measuring_threshold_transition_score = strcmp(name, "threshold_transition_score") == 0;
                int measuring_outlier_transition_score = strcmp(name, "outlier_transition_score") == 0;
                int measuring_threshold_transition_density = strcmp(name, "threshold_transition_density") == 0;
                int measuring_outlier_transition_density = strcmp(name, "outlier_transition_density") == 0;
                int measuring_threshold_transition_balance = strcmp(name, "threshold_transition_balance") == 0;
                int measuring_outlier_transition_balance = strcmp(name, "outlier_transition_balance") == 0;
                int measuring_threshold_contrast = strcmp(name, "threshold_run_contrast") == 0;
                int measuring_outlier_contrast = strcmp(name, "outlier_run_contrast") == 0;
                int measuring_threshold_contrast_delta = strcmp(name, "threshold_run_contrast_delta") == 0;
                int measuring_outlier_contrast_delta = strcmp(name, "outlier_run_contrast_delta") == 0;
                int measuring_threshold_signal = strcmp(name, "threshold_run_signal_score") == 0;
                int measuring_outlier_signal = strcmp(name, "outlier_run_signal_score") == 0;
                int measuring_threshold_signal_density = strcmp(name, "threshold_run_signal_density") == 0;
                int measuring_outlier_signal_density = strcmp(name, "outlier_run_signal_density") == 0;
                int measuring_threshold_signal_density_delta = strcmp(name, "threshold_run_signal_density_delta") == 0;
                int measuring_outlier_signal_density_delta = strcmp(name, "outlier_run_signal_density_delta") == 0;
                int measuring_threshold_signal_density_ratio = strcmp(name, "threshold_run_signal_density_ratio") == 0;
                int measuring_outlier_signal_density_ratio = strcmp(name, "outlier_run_signal_density_ratio") == 0;
                int measuring_threshold_signal_density_gap = strcmp(name, "threshold_run_signal_density_gap") == 0;
                int measuring_outlier_signal_density_gap = strcmp(name, "outlier_run_signal_density_gap") == 0;
                int measuring_threshold_signal_density_band = strcmp(name, "threshold_run_signal_density_band") == 0;
                int measuring_outlier_signal_density_band = strcmp(name, "outlier_run_signal_density_band") == 0;
                int measuring_threshold_signal_density_band_ratio = strcmp(name, "threshold_run_signal_density_band_ratio") == 0;
                int measuring_outlier_signal_density_band_ratio = strcmp(name, "outlier_run_signal_density_band_ratio") == 0;
                int measuring_threshold_signal_density_band_gap = strcmp(name, "threshold_run_signal_density_band_gap") == 0;
                int measuring_outlier_signal_density_band_gap = strcmp(name, "outlier_run_signal_density_band_gap") == 0;
                int measuring_threshold_signal_density_band_gap_ratio = strcmp(name, "threshold_run_signal_density_band_gap_ratio") == 0;
                int measuring_outlier_signal_density_band_gap_ratio = strcmp(name, "outlier_run_signal_density_band_gap_ratio") == 0;
                int measuring_threshold_signal_density_band_span = strcmp(name, "threshold_run_signal_density_band_span") == 0;
                int measuring_outlier_signal_density_band_span = strcmp(name, "outlier_run_signal_density_band_span") == 0;
                int measuring_threshold_signal_density_band_span_ratio = strcmp(name, "threshold_run_signal_density_band_span_ratio") == 0;
                int measuring_outlier_signal_density_band_span_ratio = strcmp(name, "outlier_run_signal_density_band_span_ratio") == 0;
                int measuring_threshold_signal_density_band_span_gap = strcmp(name, "threshold_run_signal_density_band_span_gap") == 0;
                int measuring_outlier_signal_density_band_span_gap = strcmp(name, "outlier_run_signal_density_band_span_gap") == 0;
                int measuring_threshold_signal_density_band_span_gap_ratio = strcmp(name, "threshold_run_signal_density_band_span_gap_ratio") == 0;
                int measuring_outlier_signal_density_band_span_gap_ratio = strcmp(name, "outlier_run_signal_density_band_span_gap_ratio") == 0;
                int measuring_threshold_signal_density_band_span_gap_delta = strcmp(name, "threshold_run_signal_density_band_span_gap_delta") == 0;
                int measuring_outlier_signal_density_band_span_gap_delta = strcmp(name, "outlier_run_signal_density_band_span_gap_delta") == 0;
                int measuring_threshold_signal_density_band_span_gap_delta_ratio = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_ratio") == 0;
                int measuring_outlier_signal_density_band_span_gap_delta_ratio = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_ratio") == 0;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_ingot = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ingot") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_steel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_smelt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_alloy") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fuse") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))))))));
                int measuring_outlier_signal_density_band_span_gap_delta_balance_ingot = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ingot") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_steel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_smelt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_alloy") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fuse") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))))))));
                int measuring_threshold_signal_density_band_span_gap_delta_balance_ore = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ore") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_ingot;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_ore = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ore") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_ingot;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_cast = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cast") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_ore;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_cast = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cast") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_ore;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_mold = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mold") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_cast;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_mold = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mold") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_cast;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_iron = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_iron") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_mold;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_iron = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_iron") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_mold;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_metal = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_metal") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_iron;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_metal = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_metal") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_iron;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_anvil = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_anvil") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_metal;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_anvil = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_anvil") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_metal;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_forge = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_forge") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_anvil;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_forge = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_forge") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_anvil;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_brand = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_brand") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_forge;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_brand = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_brand") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_forge;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_stone = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stone") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_brand;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_stone = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stone") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_brand;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_smoke = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_smoke") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_stone;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_smoke = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_smoke") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_stone;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_flame = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_flame") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_smoke;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_flame = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_flame") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_smoke;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_blaze = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_blaze") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_flame;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_blaze = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_blaze") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_flame;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_ash = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ash") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_blaze;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_ash = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ash") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_blaze;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_glow = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_glow") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_ash;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_glow = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_glow") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_ash;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_ember = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ember") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_glow;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_ember = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ember") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_glow;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_torch = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_torch") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_ember;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_torch = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_torch") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_ember;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_spark = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spark") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_torch;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_spark = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spark") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_torch;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_flare = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_flare") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_spark;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_flare = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_flare") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_spark;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_spire = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spire") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_flare;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_spire = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spire") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_flare;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_plume = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_plume") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_spire;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_plume = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_plume") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_spire;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_crest = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_crest") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_plume;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_crest = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_crest") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_plume;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_halo = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_halo") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_crest;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_halo = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_halo") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_crest;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_crown = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_crown") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_halo;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_crown = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_crown") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_halo;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_root = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_root") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_crown;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_root = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_root") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_crown;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_core = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_core") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_root;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_core = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_core") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_root;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_keep = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_keep") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_core;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_keep = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_keep") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_core;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_fort = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fort") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_keep;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_fort = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fort") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_keep;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_wall = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_wall") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_fort;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_wall = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_wall") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_fort;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_shield = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shield") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_wall;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_shield = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shield") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_wall;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_guard = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_guard") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_shield;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_guard = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_guard") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_shield;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_gate = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gate") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_guard;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_gate = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gate") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_guard;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_arch = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_arch") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_gate;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_arch = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_arch") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_gate;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_arc = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_arc") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_arch;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_arc = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_arc") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_arch;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_bow = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bow") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_arc;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_bow = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bow") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_arc;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_tie = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tie") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_bow;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_tie = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tie") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_bow;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_knot = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knot") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_tie;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_knot = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knot") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_tie;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_rope = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rope") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_knot;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_rope = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rope") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_knot;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_chain = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_chain") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_rope;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_chain = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_chain") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_rope;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_link = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_link") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_chain;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_link = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_link") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_chain;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_hook = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_hook") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_link;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_hook = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_hook") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_link;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_latch = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_latch") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_hook;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_latch = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_latch") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_hook;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_clasp = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_clasp") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_latch;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_clasp = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_clasp") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_latch;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_snap = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_snap") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_clasp;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_snap = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_snap") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_clasp;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_pin = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pin") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_snap;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_pin = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pin") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_snap;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_press = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_press") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_pin;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_press = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_press") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_pin;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_stamp = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stamp") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_press;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_stamp = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stamp") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_press;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_mark = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mark") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_stamp;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_mark = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mark") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_stamp;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_seal = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seal") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_mark;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_seal = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seal") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_mark;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_lock = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lock") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_seal;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_lock = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lock") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_seal;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_hold = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_hold") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_lock;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_hold = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_hold") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_lock;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_grip = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grip") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_hold;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_grip = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grip") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_hold;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_bite = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bite") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_grip;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_bite = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bite") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_grip;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_jaw = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jaw") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_bite;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_jaw = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jaw") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_bite;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_lip = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lip") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_jaw;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_lip = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lip") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_jaw;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_rim = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rim") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_lip;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_rim = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rim") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_lip;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_edge = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_edge") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_rim;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_edge = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_edge") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_rim;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_tail = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tail") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_edge;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_tail = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tail") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_edge;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_peak = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_peak") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_tail;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_peak = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_peak") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_tail;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_wave = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_wave") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_peak;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_wave = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_wave") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_peak;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_flux = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_flux") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_wave;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_flux = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_flux") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_wave;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_load = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_load") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_flux;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_load = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_load") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_flux;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_mass = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mass") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_load;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_mass = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mass") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_load;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_spread = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spread") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_mass;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_spread = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spread") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_mass;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_drift = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_drift") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_spread;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_drift = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_drift") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_spread;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_delta_ratio = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_count") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_drift;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_delta_ratio = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_count") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_drift;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_delta = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_delta") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_delta_ratio;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_delta = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_delta") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_delta_ratio;
                int measuring_threshold_signal_density_band_span_gap_delta_balance_ratio = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ratio") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_delta;
                int measuring_outlier_signal_density_band_span_gap_delta_balance_ratio = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ratio") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_delta;
                int measuring_threshold_signal_density_band_span_gap_delta_balance = strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance") == 0 || measuring_threshold_signal_density_band_span_gap_delta_balance_ratio;
                int measuring_outlier_signal_density_band_span_gap_delta_balance = strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance") == 0 || measuring_outlier_signal_density_band_span_gap_delta_balance_ratio;
                int measuring_transition_score = measuring_threshold_transition_score || measuring_outlier_transition_score || measuring_threshold_transition_density || measuring_outlier_transition_density || measuring_threshold_transition_balance || measuring_outlier_transition_balance || measuring_threshold_contrast || measuring_outlier_contrast || measuring_threshold_contrast_delta || measuring_outlier_contrast_delta || measuring_threshold_signal || measuring_outlier_signal || measuring_threshold_signal_density || measuring_outlier_signal_density || measuring_threshold_signal_density_delta || measuring_outlier_signal_density_delta || measuring_threshold_signal_density_ratio || measuring_outlier_signal_density_ratio || measuring_threshold_signal_density_gap || measuring_outlier_signal_density_gap || measuring_threshold_signal_density_band || measuring_outlier_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance;
                int scoring_threshold_runs = strcmp(name, "threshold_run_score") == 0 || strcmp(name, "threshold_run_length_score") == 0;
                int scoring_outlier_runs = strcmp(name, "outlier_run_length_score") == 0;
                int collecting_threshold_lengths = strcmp(name, "threshold_run_lengths") == 0;
                int collecting_outlier_lengths = strcmp(name, "outlier_run_lengths") == 0;
                int collecting_lengths = collecting_threshold_lengths || collecting_outlier_lengths;

                if (argument_count != 3) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &lower_bound)) {
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[2], &upper_bound)) {
                    return integer_value(0);
                }
                if (measuring_transition_score) {
                    size_t run_start = 0;
                    long matching_mass = 0;
                    long matching_run_count = 0;
                    long transition_count = 0;
                    long continuity_score = 0;
                    long transition_balance = 0;
                    while (run_start < array->element_count) {
                        size_t run_end = run_start + 1;
                        int run_in_range = array->elements[run_start] >= lower_bound && array->elements[run_start] <= upper_bound;
                        int left_transition = run_start > 0;
                        int right_transition;
                        if (left_transition) {
                            transition_count++;
                        }
                        while (run_end < array->element_count) {
                            int next_in_range = array->elements[run_end] >= lower_bound && array->elements[run_end] <= upper_bound;
                            if (next_in_range != run_in_range) {
                                break;
                            }
                            run_end++;
                        }
                        right_transition = run_end < array->element_count;
                        if (((measuring_threshold_transition_score || measuring_threshold_transition_density || measuring_threshold_transition_balance || measuring_threshold_contrast || measuring_threshold_contrast_delta || measuring_threshold_signal || measuring_threshold_signal_density || measuring_threshold_signal_density_delta || measuring_threshold_signal_density_ratio || measuring_threshold_signal_density_gap || measuring_threshold_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance) && run_in_range) || ((measuring_outlier_transition_score || measuring_outlier_transition_density || measuring_outlier_transition_balance || measuring_outlier_contrast || measuring_outlier_contrast_delta || measuring_outlier_signal || measuring_outlier_signal_density || measuring_outlier_signal_density_delta || measuring_outlier_signal_density_ratio || measuring_outlier_signal_density_gap || measuring_outlier_signal_density_band || measuring_outlier_signal_density_band_ratio || measuring_outlier_signal_density_band_gap || measuring_outlier_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_span || measuring_outlier_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_balance) && !run_in_range)) {
                            long boundary_count = (left_transition ? 1 : 0) + (right_transition ? 1 : 0);
                            long run_length = (long)(run_end - run_start);
                            matched += run_length * boundary_count;
                            matching_mass += run_length;
                            matching_run_count++;
                            continuity_score += run_length - 1;
                            if (run_length > longest_run) {
                                longest_run = run_length;
                            }
                            if (shortest_run == 0 || run_length < shortest_run) {
                                shortest_run = run_length;
                            }
                        }
                        run_start = run_end;
                    }
                    if (measuring_threshold_transition_density || measuring_outlier_transition_density || measuring_threshold_transition_balance || measuring_outlier_transition_balance || measuring_threshold_contrast || measuring_outlier_contrast || measuring_threshold_contrast_delta || measuring_outlier_contrast_delta || measuring_threshold_signal || measuring_outlier_signal || measuring_threshold_signal_density || measuring_outlier_signal_density || measuring_threshold_signal_density_delta || measuring_outlier_signal_density_delta || measuring_threshold_signal_density_ratio || measuring_outlier_signal_density_ratio || measuring_threshold_signal_density_gap || measuring_outlier_signal_density_gap || measuring_threshold_signal_density_band || measuring_outlier_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 0 ? matched / matching_mass : 0;
                    }
                    transition_balance = matching_mass > 0 ? matched - continuity_score : 0;
                    if (measuring_threshold_transition_balance || measuring_outlier_transition_balance) {
                        matched = transition_balance;
                    }
                    if (measuring_threshold_contrast || measuring_outlier_contrast || measuring_threshold_contrast_delta || measuring_outlier_contrast_delta || measuring_threshold_signal || measuring_outlier_signal || measuring_threshold_signal_density || measuring_outlier_signal_density || measuring_threshold_signal_density_delta || measuring_outlier_signal_density_delta || measuring_threshold_signal_density_ratio || measuring_outlier_signal_density_ratio || measuring_threshold_signal_density_gap || measuring_outlier_signal_density_gap || measuring_threshold_signal_density_band || measuring_outlier_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 0 ? continuity_score - (matched - continuity_score) : 0;
                    }
                    if ((measuring_threshold_contrast_delta || measuring_outlier_contrast_delta || measuring_threshold_signal || measuring_outlier_signal || measuring_threshold_signal_density || measuring_outlier_signal_density || measuring_threshold_signal_density_delta || measuring_outlier_signal_density_delta || measuring_threshold_signal_density_ratio || measuring_outlier_signal_density_ratio || measuring_threshold_signal_density_gap || measuring_outlier_signal_density_gap || measuring_threshold_signal_density_band || measuring_outlier_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run - shortest_run;
                    }
                    if (measuring_threshold_signal || measuring_outlier_signal || measuring_threshold_signal_density || measuring_outlier_signal_density || measuring_threshold_signal_density_delta || measuring_outlier_signal_density_delta || measuring_threshold_signal_density_ratio || measuring_outlier_signal_density_ratio || measuring_threshold_signal_density_gap || measuring_outlier_signal_density_gap || measuring_threshold_signal_density_band || measuring_outlier_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 0 ? matched + continuity_score : 0;
                    }
                    if (measuring_threshold_signal_density || measuring_outlier_signal_density || measuring_threshold_signal_density_delta || measuring_outlier_signal_density_delta || measuring_threshold_signal_density_ratio || measuring_outlier_signal_density_ratio || measuring_threshold_signal_density_gap || measuring_outlier_signal_density_gap || measuring_threshold_signal_density_band || measuring_outlier_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 0 ? matched / matching_mass : 0;
                    }
                    if ((measuring_threshold_signal_density_delta || measuring_outlier_signal_density_delta || measuring_threshold_signal_density_ratio || measuring_outlier_signal_density_ratio || measuring_threshold_signal_density_gap || measuring_outlier_signal_density_gap || measuring_threshold_signal_density_band || measuring_outlier_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run - shortest_run;
                    }
                    if (measuring_threshold_signal_density_ratio || measuring_outlier_signal_density_ratio || measuring_threshold_signal_density_gap || measuring_outlier_signal_density_gap || measuring_threshold_signal_density_band || measuring_outlier_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 1 && matching_run_count > 0 ? matched - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_gap || measuring_outlier_signal_density_gap || measuring_threshold_signal_density_band || measuring_outlier_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 1 ? matched - transition_balance : 0;
                    }
                    if ((measuring_threshold_signal_density_band || measuring_outlier_signal_density_band || measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_ratio || measuring_outlier_signal_density_band_ratio || measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 1 && matching_run_count > 0 ? matched - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_gap || measuring_outlier_signal_density_band_gap || measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 1 ? matched - transition_balance : 0;
                    }
                    if (measuring_threshold_signal_density_band_gap_ratio || measuring_outlier_signal_density_band_gap_ratio || measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 1 && matching_run_count > 0 ? matched - matching_run_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span || measuring_outlier_signal_density_band_span || measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_ratio || measuring_outlier_signal_density_band_span_ratio || measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 1 && matching_run_count > 0 ? matched - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap || measuring_outlier_signal_density_band_span_gap || measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 1 ? matched - transition_balance : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_ratio || measuring_outlier_signal_density_band_span_gap_ratio || measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 1 && matching_run_count > 0 ? matched - matching_run_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta || measuring_outlier_signal_density_band_span_gap_delta || measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run - shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_ratio || measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 1 && matching_run_count > 0 ? matched - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance || measuring_outlier_signal_density_band_span_gap_delta_balance) {
                        matched = matching_mass > 1 ? matched - transition_balance : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_ratio || measuring_outlier_signal_density_band_span_gap_delta_balance_ratio) {
                        matched = matching_mass > 1 && matching_run_count > 0 ? matched - matching_run_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_delta || measuring_outlier_signal_density_band_span_gap_delta_balance_delta) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run - shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_delta_ratio || measuring_outlier_signal_density_band_span_gap_delta_balance_delta_ratio) {
                        matched = matching_mass > 1 && matching_run_count > 0 ? matched - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_drift || measuring_outlier_signal_density_band_span_gap_delta_balance_drift) {
                        matched = matching_mass > 1 ? matched - transition_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_spread || measuring_outlier_signal_density_band_span_gap_delta_balance_spread) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_mass || measuring_outlier_signal_density_band_span_gap_delta_balance_mass) {
                        matched = matching_mass > 1 ? matched - matching_mass : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_load || measuring_outlier_signal_density_band_span_gap_delta_balance_load) {
                        matched = matching_mass > 1 ? matched - continuity_score : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_flux || measuring_outlier_signal_density_band_span_gap_delta_balance_flux) {
                        matched = matching_mass > 1 ? matched - transition_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_wave || measuring_outlier_signal_density_band_span_gap_delta_balance_wave) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run * shortest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_peak || measuring_outlier_signal_density_band_span_gap_delta_balance_peak) && matching_mass > 1 && longest_run > 0) {
                        matched -= longest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_tail || measuring_outlier_signal_density_band_span_gap_delta_balance_tail) && matching_mass > 1 && shortest_run > 0) {
                        matched -= shortest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_edge || measuring_outlier_signal_density_band_span_gap_delta_balance_edge) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_rim || measuring_outlier_signal_density_band_span_gap_delta_balance_rim) {
                        matched = matching_mass > 1 && matching_run_count > 0 ? matched - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_lip || measuring_outlier_signal_density_band_span_gap_delta_balance_lip) {
                        matched = matching_mass > 1 ? matched - transition_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_jaw || measuring_outlier_signal_density_band_span_gap_delta_balance_jaw) {
                        matched = matching_mass > 1 ? matched - matching_mass - matching_run_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_bite || measuring_outlier_signal_density_band_span_gap_delta_balance_bite) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= transition_count + longest_run + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_grip || measuring_outlier_signal_density_band_span_gap_delta_balance_grip) {
                        matched = matching_mass > 1 ? matched - continuity_score - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_hold || measuring_outlier_signal_density_band_span_gap_delta_balance_hold) {
                        matched = matching_mass > 1 ? matched - matching_mass - continuity_score : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_lock || measuring_outlier_signal_density_band_span_gap_delta_balance_lock) {
                        matched = matching_mass > 1 ? matched - transition_count - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_seal || measuring_outlier_signal_density_band_span_gap_delta_balance_seal) {
                        matched = matching_mass > 1 ? matched - matching_mass - transition_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_mark || measuring_outlier_signal_density_band_span_gap_delta_balance_mark) {
                        matched = matching_mass > 1 ? matched - matching_mass - continuity_score - matching_run_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_stamp || measuring_outlier_signal_density_band_span_gap_delta_balance_stamp) && matching_mass > 1 && longest_run > 0) {
                        matched -= transition_count + longest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_press || measuring_outlier_signal_density_band_span_gap_delta_balance_press) && matching_mass > 1 && shortest_run > 0) {
                        matched -= transition_count + shortest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_pin || measuring_outlier_signal_density_band_span_gap_delta_balance_pin) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_run_count + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_snap || measuring_outlier_signal_density_band_span_gap_delta_balance_snap) {
                        matched = matching_mass > 1 ? matched - transition_count - matching_run_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_clasp || measuring_outlier_signal_density_band_span_gap_delta_balance_clasp) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= matching_mass + longest_run + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_latch || measuring_outlier_signal_density_band_span_gap_delta_balance_latch) {
                        matched = matching_mass > 1 ? matched - transition_count - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_hook || measuring_outlier_signal_density_band_span_gap_delta_balance_hook) {
                        matched = matching_mass > 1 ? matched - transition_count - longest_run : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_link || measuring_outlier_signal_density_band_span_gap_delta_balance_link) && matching_mass > 1 && shortest_run > 0) {
                        matched -= transition_count + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_chain || measuring_outlier_signal_density_band_span_gap_delta_balance_chain) {
                        matched = matching_mass > 1 ? matched - transition_count - matching_mass : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_rope || measuring_outlier_signal_density_band_span_gap_delta_balance_rope) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= transition_count + longest_run + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_knot || measuring_outlier_signal_density_band_span_gap_delta_balance_knot) {
                        matched = matching_mass > 1 ? matched - matching_mass : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_tie || measuring_outlier_signal_density_band_span_gap_delta_balance_tie) {
                        matched = matching_mass > 1 ? matched - matching_run_count - transition_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_bow || measuring_outlier_signal_density_band_span_gap_delta_balance_bow) && matching_mass > 1 && longest_run > 0) {
                        matched -= longest_run + matching_run_count;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_arc || measuring_outlier_signal_density_band_span_gap_delta_balance_arc) && matching_mass > 1 && shortest_run > 0) {
                        matched -= transition_count + shortest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_arch || measuring_outlier_signal_density_band_span_gap_delta_balance_arch) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= transition_count + longest_run + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_gate || measuring_outlier_signal_density_band_span_gap_delta_balance_gate) {
                        matched = matching_mass > 1 ? matched - matching_mass - matching_run_count - transition_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_guard || measuring_outlier_signal_density_band_span_gap_delta_balance_guard) {
                        matched = matching_mass > 1 ? matched - continuity_score - matching_run_count - transition_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_shield || measuring_outlier_signal_density_band_span_gap_delta_balance_shield) {
                        matched = matching_mass > 1 ? matched - matching_mass : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_wall || measuring_outlier_signal_density_band_span_gap_delta_balance_wall) {
                        matched = matching_mass > 1 ? matched - transition_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_fort || measuring_outlier_signal_density_band_span_gap_delta_balance_fort) {
                        matched = matching_mass > 1 ? matched - matching_mass - transition_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_keep || measuring_outlier_signal_density_band_span_gap_delta_balance_keep) {
                        matched = matching_mass > 1 ? matched - continuity_score : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_core || measuring_outlier_signal_density_band_span_gap_delta_balance_core) {
                        matched = matching_mass > 1 ? matched - matching_mass - continuity_score - transition_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_root || measuring_outlier_signal_density_band_span_gap_delta_balance_root) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= matching_run_count + longest_run + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_crown || measuring_outlier_signal_density_band_span_gap_delta_balance_crown) {
                        matched = matching_mass > 1 ? matched - matching_mass - transition_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_halo || measuring_outlier_signal_density_band_span_gap_delta_balance_halo) {
                        matched = matching_mass > 1 ? matched - continuity_score - transition_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_crest || measuring_outlier_signal_density_band_span_gap_delta_balance_crest) && matching_mass > 1 && longest_run > 0) {
                        matched -= longest_run + transition_count;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_plume || measuring_outlier_signal_density_band_span_gap_delta_balance_plume) && matching_mass > 1 && shortest_run > 0) {
                        matched -= shortest_run + transition_count;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_spire || measuring_outlier_signal_density_band_span_gap_delta_balance_spire) {
                        matched = matching_mass > 1 ? matched - matching_run_count - transition_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_flare || measuring_outlier_signal_density_band_span_gap_delta_balance_flare) {
                        matched = matching_mass > 1 ? matched - matching_mass - transition_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_spark || measuring_outlier_signal_density_band_span_gap_delta_balance_spark) {
                        matched = matching_mass > 1 ? matched - continuity_score - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_torch || measuring_outlier_signal_density_band_span_gap_delta_balance_torch) {
                        matched = matching_mass > 1 ? matched - continuity_score - transition_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_ember || measuring_outlier_signal_density_band_span_gap_delta_balance_ember) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + shortest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_glow || measuring_outlier_signal_density_band_span_gap_delta_balance_glow) && matching_mass > 1 && longest_run > 0) {
                        matched -= longest_run + matching_run_count;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_ash || measuring_outlier_signal_density_band_span_gap_delta_balance_ash) && matching_mass > 1 && shortest_run > 0) {
                        matched -= transition_count + shortest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_blaze || measuring_outlier_signal_density_band_span_gap_delta_balance_blaze) && matching_mass > 1 && longest_run > 0) {
                        matched -= longest_run + transition_count;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_flame || measuring_outlier_signal_density_band_span_gap_delta_balance_flame) && matching_mass > 1 && longest_run > 0) {
                        matched -= matching_mass + longest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_smoke || measuring_outlier_signal_density_band_span_gap_delta_balance_smoke) {
                        matched = matching_mass > 1 ? matched - transition_count - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_stone || measuring_outlier_signal_density_band_span_gap_delta_balance_stone) {
                        matched = matching_mass > 1 ? matched - matching_mass - matching_run_count : 0;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_brand || measuring_outlier_signal_density_band_span_gap_delta_balance_brand) {
                        matched = matching_mass > 1 ? matched - matching_mass - transition_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_forge || measuring_outlier_signal_density_band_span_gap_delta_balance_forge) && matching_mass > 1 && longest_run > 0) {
                        matched -= matching_mass + longest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_anvil || measuring_outlier_signal_density_band_span_gap_delta_balance_anvil) && matching_mass > 1 && shortest_run > 0) {
                        matched -= shortest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_metal || measuring_outlier_signal_density_band_span_gap_delta_balance_metal) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + shortest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_iron || measuring_outlier_signal_density_band_span_gap_delta_balance_iron) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run + shortest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_mold || measuring_outlier_signal_density_band_span_gap_delta_balance_mold) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= matching_mass + longest_run + shortest_run;
                    }
                    if (measuring_threshold_signal_density_band_span_gap_delta_balance_cast || measuring_outlier_signal_density_band_span_gap_delta_balance_cast) {
                        matched = matching_mass > 1 ? matched - matching_mass - transition_count : 0;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_ore || measuring_outlier_signal_density_band_span_gap_delta_balance_ore) && matching_mass > 1 && longest_run > 0) {
                        matched -= transition_count + longest_run;
                    }
                    if ((measuring_threshold_signal_density_band_span_gap_delta_balance_ingot || measuring_outlier_signal_density_band_span_gap_delta_balance_ingot) && matching_mass > 1 && longest_run > 0) {
                        matched -= matching_mass + transition_count + longest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_steel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_steel") == 0) && matching_mass > 1 && shortest_run > 0) {
                        matched -= shortest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_smelt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_smelt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_alloy") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_alloy") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fuse") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fuse") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + shortest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_alloy") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_alloy") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fuse") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fuse") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= transition_count + shortest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fuse") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fuse") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braze") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run + shortest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_meld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= matching_mass + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weld") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_solder") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= transition_count + shortest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0) {
                        long rivet_pressure = matching_mass + longest_run;
                        if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rivet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))) && matching_run_count == 1) {
                            rivet_pressure--;
                        }
                        matched -= rivet_pressure;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bolt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= transition_count + matching_run_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_screw") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + shortest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_nail") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0) {
                        matched -= transition_count + longest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_thread") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_weave") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run + shortest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_stitch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= matching_mass + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lace") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && matching_run_count > 0 && shortest_run > 0) {
                        matched -= shortest_run + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cord") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0) {
                        matched -= matching_mass + longest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_fiber") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + shortest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_strand") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= transition_count + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_twine") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= matching_mass + transition_count + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_yarn") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0 && matching_run_count > 0) {
                        matched -= matching_mass + longest_run + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loom") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))))) && matching_mass > 1 && shortest_run > 0 && matching_run_count > 0) {
                        matched -= matching_mass + shortest_run + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_braid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run + shortest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_mesh") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_net") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= transition_count + matching_run_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_web") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0) {
                        matched -= matching_mass + transition_count + longest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_grid") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + transition_count + shortest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cloth") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0) {
                        matched -= matching_mass + transition_count + longest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_knit") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + transition_count + shortest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_loop") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run + shortest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_tile") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= matching_mass + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_patch") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_seam") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))))) && matching_mass > 1 && longest_run > 0 && matching_run_count > 0) {
                        matched -= longest_run + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_node") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))))) && matching_mass > 1 && shortest_run > 0 && matching_run_count > 0) {
                        matched -= shortest_run + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ring") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_bead") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))))) && matching_mass > 1 && longest_run > 0) {
                        matched -= longest_run + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_charm") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= matching_mass + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gem") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jewel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))))) && matching_mass > 1 && longest_run > 0 && matching_run_count > 0) {
                        matched -= longest_run + matching_run_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_facet") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= shortest_run + transition_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_prism") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))) && matching_mass > 1 && longest_run > 0) {
                        matched -= matching_mass + longest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_opal") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + shortest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_ruby") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= transition_count + matching_run_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pearl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= matching_mass + longest_run + shortest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_agate") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_topaz") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))))) && matching_mass > 1 && longest_run > 0) {
                        matched -= longest_run + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_amber") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + shortest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_garnet") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))))) && matching_mass > 1 && longest_run > 0 && matching_run_count > 0) {
                        matched -= longest_run + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_onyx") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_quartz") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))))) && matching_mass > 1 && longest_run > 0 && shortest_run > 0) {
                        matched -= longest_run + shortest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jade") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= matching_mass + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_beryl") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_coral") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))) && matching_mass > 1 && longest_run > 0) {
                        matched -= longest_run + transition_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_lapis") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= shortest_run + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_zircon") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_spinel") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= longest_run + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_jasper") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + shortest_run;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_marble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_basalt") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))))) && matching_mass > 1 && longest_run > 0) {
                        matched -= matching_mass + longest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_slate") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + shortest_run;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shale") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_shard") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= longest_run + matching_run_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_gravel") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))) || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_pebble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))) && matching_mass > 1 && longest_run > 0) {
                        matched -= longest_run + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cobble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))))) && matching_mass > 1 && matching_run_count > 0) {
                        matched -= matching_mass + matching_run_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0))) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_rubble") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)))) && matching_mass > 1) {
                        matched -= matching_mass + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0)) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_talus") == 0 || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0))) && matching_mass > 1 && longest_run > 0) {
                        matched -= longest_run + transition_count;
                    }
                    if (((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0) || (strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_scree") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0)) && matching_mass > 1 && shortest_run > 0) {
                        matched -= shortest_run + transition_count;
                    }
                    if ((strcmp(name, "threshold_run_signal_density_band_span_gap_delta_balance_cairn") == 0 || strcmp(name, "outlier_run_signal_density_band_span_gap_delta_balance_cairn") == 0) && matching_mass > 1 && shortest_run > 0) {
                        matched -= matching_mass + shortest_run;
                    }
                    compact_unreferenced_arrays(parser, &arguments[0]);
                    return parse_index_postfix(parser, integer_value(matched));
                }
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    int in_range = array->elements[element_index] >= lower_bound && array->elements[element_index] <= upper_bound;
                    if (measuring_transition_count) {
                        if (has_previous_range_state && previous_in_range != in_range) {
                            matched++;
                        }
                        previous_in_range = in_range;
                        has_previous_range_state = 1;
                    } else if (measuring_threshold_longest) {
                        if (in_range) {
                            current_streak++;
                            if (current_streak > matched) {
                                matched = current_streak;
                            }
                        } else {
                            current_streak = 0;
                        }
                    } else if (measuring_threshold_shortest) {
                        if (in_range) {
                            current_streak++;
                        } else if (current_streak > 0) {
                            if (matched == 0 || current_streak < matched) {
                                matched = current_streak;
                            }
                            current_streak = 0;
                        }
                    } else if (measuring_outlier_shortest) {
                        if (!in_range) {
                            current_streak++;
                        } else if (current_streak > 0) {
                            if (matched == 0 || current_streak < matched) {
                                matched = current_streak;
                            }
                            current_streak = 0;
                        }
                    } else if (measuring_outlier_delta) {
                        if (!in_range) {
                            current_streak++;
                        } else if (current_streak > 0) {
                            if (current_streak > longest_run) {
                                longest_run = current_streak;
                            }
                            if (shortest_run == 0 || current_streak < shortest_run) {
                                shortest_run = current_streak;
                            }
                            current_streak = 0;
                        }
                    } else if (measuring_outlier_ratio) {
                        if (!in_range) {
                            current_streak++;
                        } else if (current_streak > 0) {
                            matched += current_streak - 1;
                            current_streak = 0;
                        }
                    } else if (measuring_outlier_streak) {
                        if (!in_range) {
                            current_streak++;
                            if (current_streak > matched) {
                                matched = current_streak;
                            }
                        } else {
                            current_streak = 0;
                        }
                    } else if (measuring_outlier_runs) {
                        if (!in_range) {
                            if (current_streak == 0) {
                                matched++;
                            }
                            current_streak = 1;
                        } else {
                            current_streak = 0;
                        }
                    } else if (collecting_outlier_lengths || scoring_outlier_runs) {
                        if (!in_range) {
                            current_streak++;
                        } else if (current_streak > 0) {
                            if (scoring_outlier_runs) {
                                matched += current_streak * current_streak;
                            } else {
                                run_lengths[run_count] = current_streak;
                                run_count++;
                            }
                            current_streak = 0;
                        }
                    } else if (measuring_threshold_delta) {
                        if (in_range) {
                            current_streak++;
                        } else if (current_streak > 0) {
                            if (current_streak > longest_run) {
                                longest_run = current_streak;
                            }
                            if (shortest_run == 0 || current_streak < shortest_run) {
                                shortest_run = current_streak;
                            }
                            current_streak = 0;
                        }
                    } else if (measuring_threshold_ratio) {
                        if (in_range) {
                            current_streak++;
                        } else if (current_streak > 0) {
                            matched += current_streak - 1;
                            current_streak = 0;
                        }
                    } else if (in_range) {
                        current_streak++;
                    } else {
                        if (scoring_threshold_runs) {
                            matched += current_streak * current_streak;
                        } else if (collecting_threshold_lengths) {
                            if (current_streak > 0) {
                                run_lengths[run_count] = current_streak;
                                run_count++;
                            }
                        } else if (current_streak > 0) {
                            matched++;
                        }
                        current_streak = 0;
                    }
                }
                if (collecting_lengths) {
                    struct ArrayValue *result_array;
                    struct Value value;
                    if (current_streak > 0) {
                        run_lengths[run_count] = current_streak;
                        run_count++;
                    }
                    compact_unreferenced_arrays(parser, &arguments[0]);
                    if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                        parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                        return integer_value(0);
                    }
                    result_array = &parser->arrays[parser->array_count];
                    result_array->element_count = run_count;
                    result_array->scope_depth = parser->scope_depth;
                    result_array->id = parser->next_array_id;
                    result_array->under_construction = 0;
                    for (element_index = 0; element_index < run_count; element_index++) {
                        result_array->elements[element_index] = run_lengths[element_index];
                    }
                    value = array_value(parser->array_count, result_array->id);
                    parser->array_count++;
                    parser->next_array_id++;
                    return parse_index_postfix(parser, value);
                }
                if ((measuring_threshold_delta || measuring_outlier_delta) && current_streak > 0) {
                    if (current_streak > longest_run) {
                        longest_run = current_streak;
                    }
                    if (shortest_run == 0 || current_streak < shortest_run) {
                        shortest_run = current_streak;
                    }
                }
                if (measuring_threshold_delta || measuring_outlier_delta) {
                    if (longest_run > 0 && shortest_run > 0) {
                        matched = longest_run - shortest_run;
                    }
                } else if ((measuring_threshold_ratio || measuring_outlier_ratio) && current_streak > 0) {
                    matched += current_streak - 1;
                } else if (scoring_threshold_runs || scoring_outlier_runs) {
                    matched += current_streak * current_streak;
                } else if ((measuring_outlier_shortest || measuring_threshold_shortest) && current_streak > 0) {
                    if (matched == 0 || current_streak < matched) {
                        matched = current_streak;
                    }
                } else if (!measuring_transition_count && !measuring_outlier_streak && !measuring_outlier_runs && !measuring_threshold_longest && !measuring_threshold_shortest && !measuring_threshold_ratio && !measuring_outlier_ratio && current_streak > 0) {
                    matched++;
                }
                compact_unreferenced_arrays(parser, &arguments[0]);
                return parse_index_postfix(parser, integer_value(matched));
            }

            if (strcmp(name, "histogram_distance_score") == 0 || strcmp(name, "histogram_within_distance") == 0) {
                struct ArrayValue *values;
                struct ArrayValue *counts;
                struct ArrayValue *expected;
                long score = 0;
                long limit = 0;
                size_t value_index;
                size_t expected_index;
                int checking_limit = strcmp(name, "histogram_within_distance") == 0;

                if (argument_count != (checking_limit ? 4 : 3)) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                values = array_from_value(parser, arguments[0]);
                if (values == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                counts = array_from_value(parser, arguments[1]);
                if (counts == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                expected = array_from_value(parser, arguments[2]);
                if (expected == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (checking_limit) {
                    if (!value_as_integer(parser, arguments[3], &limit)) {
                        return integer_value(0);
                    }
                    if (limit < 0) {
                        parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
                        return integer_value(0);
                    }
                }
                if (values->element_count != counts->element_count) {
                    parser->status = RUSTIC_ERR_ARRAY_LENGTH_MISMATCH;
                    return integer_value(0);
                }
                for (value_index = 0; value_index < values->element_count; value_index++) {
                    long expected_count = 0;
                    long difference;
                    for (expected_index = 0; expected_index < expected->element_count; expected_index++) {
                        if (expected->elements[expected_index] == values->elements[value_index]) {
                            expected_count++;
                        }
                    }
                    difference = counts->elements[value_index] - expected_count;
                    if (difference < 0) {
                        difference = -difference;
                    }
                    score += difference;
                }
                for (expected_index = 0; expected_index < expected->element_count; expected_index++) {
                    int present = 0;
                    for (value_index = 0; value_index < values->element_count; value_index++) {
                        if (expected->elements[expected_index] == values->elements[value_index]) {
                            present = 1;
                            break;
                        }
                    }
                    if (!present) {
                        score++;
                    }
                }
                compact_unreferenced_arrays(parser, NULL);
                if (checking_limit) {
                    return parse_index_postfix(parser, integer_value(score <= limit ? 1 : 0));
                }
                return parse_index_postfix(parser, integer_value(score));
            }

            if (strcmp(name, "weighted_score") == 0) {
                struct ArrayValue *source_array;
                struct Function *weighter;
                long source_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                size_t source_count;
                size_t element_index;
                long score = 0;
                long weighted;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                source_array = array_from_value(parser, arguments[0]);
                if (source_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                weighter = function_from_value(parser, arguments[1]);
                if (weighter == NULL) {
                    parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
                    return integer_value(0);
                }
                if (weighter->parameter_count != 1) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }

                source_count = source_array->element_count;
                for (element_index = 0; element_index < source_count; element_index++) {
                    source_elements[element_index] = source_array->elements[element_index];
                }
                for (element_index = 0; element_index < source_count; element_index++) {
                    struct Value weighted_value = call_unary_function(parser, weighter, source_elements[element_index]);
                    if (parser->status != RUSTIC_OK || !value_as_integer(parser, weighted_value, &weighted)) {
                        return integer_value(0);
                    }
                    score += weighted;
                }
                compact_unreferenced_arrays(parser, &arguments[0]);
                return parse_index_postfix(parser, integer_value(score));
            }

            if (strcmp(name, "clamp") == 0) {
                struct ArrayValue *array;
                long result_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long lower_bound;
                long upper_bound;
                size_t element_index;
                size_t result_count;

                if (argument_count != 3) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &lower_bound)) {
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[2], &upper_bound)) {
                    return integer_value(0);
                }
                result_count = array->element_count;
                for (element_index = 0; element_index < result_count; element_index++) {
                    long clamped = array->elements[element_index];
                    if (clamped < lower_bound) {
                        clamped = lower_bound;
                    }
                    if (clamped > upper_bound) {
                        clamped = upper_bound;
                    }
                    result_elements[element_index] = clamped;
                }
                compact_unreferenced_arrays(parser, NULL);
                if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }
                array = &parser->arrays[parser->array_count];
                array->element_count = result_count;
                array->scope_depth = parser->scope_depth;
                array->id = parser->next_array_id;
                array->under_construction = 0;
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    array->elements[element_index] = result_elements[element_index];
                }
                value = array_value(parser->array_count, array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (strcmp(name, "nth_sorted") == 0 || strcmp(name, "top_count") == 0 || strcmp(name, "rank_of") == 0 || strcmp(name, "top_sum") == 0) {
                struct ArrayValue *array;
                long sorted_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long result_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long requested_count;
                long scalar_result = 0;
                size_t element_index;
                size_t scan_index;
                size_t result_count;
                int building_top_count = strcmp(name, "top_count") == 0;
                int finding_rank = strcmp(name, "rank_of") == 0;
                int summing_top = strcmp(name, "top_sum") == 0;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &requested_count)) {
                    return integer_value(0);
                }
                if (!finding_rank && requested_count < 0) {
                    parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
                    return integer_value(0);
                }
                if (!building_top_count && !finding_rank && !summing_top && array->element_count == 0) {
                    parser->status = RUSTIC_ERR_EMPTY_ARRAY;
                    return integer_value(0);
                }
                if (!building_top_count && !finding_rank && !summing_top && (size_t)requested_count >= array->element_count) {
                    parser->status = RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS;
                    return integer_value(0);
                }
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    sorted_elements[element_index] = array->elements[element_index];
                }
                for (element_index = 1; element_index < array->element_count; element_index++) {
                    long current = sorted_elements[element_index];
                    scan_index = element_index;
                    while (scan_index > 0 && sorted_elements[scan_index - 1] > current) {
                        sorted_elements[scan_index] = sorted_elements[scan_index - 1];
                        scan_index--;
                    }
                    sorted_elements[scan_index] = current;
                }
                if (finding_rank) {
                    scalar_result = -1;
                    for (element_index = 0; element_index < array->element_count; element_index++) {
                        if (sorted_elements[element_index] == requested_count) {
                            scalar_result = (long)element_index;
                            break;
                        }
                    }
                    compact_unreferenced_arrays(parser, &arguments[0]);
                    return parse_index_postfix(parser, integer_value(scalar_result));
                }
                if (summing_top) {
                    result_count = (size_t)requested_count;
                    if (result_count > array->element_count) {
                        result_count = array->element_count;
                    }
                    for (element_index = 0; element_index < result_count; element_index++) {
                        scalar_result += sorted_elements[array->element_count - element_index - 1];
                    }
                    compact_unreferenced_arrays(parser, &arguments[0]);
                    return parse_index_postfix(parser, integer_value(scalar_result));
                }
                if (!building_top_count) {
                    long selected = sorted_elements[(size_t)requested_count];
                    compact_unreferenced_arrays(parser, &arguments[0]);
                    return parse_index_postfix(parser, integer_value(selected));
                }
                result_count = (size_t)requested_count;
                if (result_count > array->element_count) {
                    result_count = array->element_count;
                }
                for (element_index = 0; element_index < result_count; element_index++) {
                    result_elements[element_index] = sorted_elements[array->element_count - element_index - 1];
                }
                compact_unreferenced_arrays(parser, NULL);
                if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }
                array = &parser->arrays[parser->array_count];
                array->element_count = result_count;
                array->scope_depth = parser->scope_depth;
                array->id = parser->next_array_id;
                array->under_construction = 0;
                for (element_index = 0; element_index < result_count; element_index++) {
                    array->elements[element_index] = result_elements[element_index];
                }
                value = array_value(parser->array_count, array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (strcmp(name, "unique_count") == 0 || strcmp(name, "histogram_count") == 0 || strcmp(name, "histogram_values") == 0) {
                struct ArrayValue *array;
                long sorted_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long result_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                size_t element_index;
                size_t scan_index;
                size_t unique_total = 0;
                int building_histogram = strcmp(name, "histogram_count") == 0;
                int building_values = strcmp(name, "histogram_values") == 0;

                if (argument_count != 1) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    sorted_elements[element_index] = array->elements[element_index];
                }
                for (element_index = 1; element_index < array->element_count; element_index++) {
                    long current = sorted_elements[element_index];
                    scan_index = element_index;
                    while (scan_index > 0 && sorted_elements[scan_index - 1] > current) {
                        sorted_elements[scan_index] = sorted_elements[scan_index - 1];
                        scan_index--;
                    }
                    sorted_elements[scan_index] = current;
                }
                for (element_index = 0; element_index < array->element_count; element_index++) {
                    if (element_index == 0 || sorted_elements[element_index] != sorted_elements[element_index - 1]) {
                        result_elements[unique_total] = building_values ? sorted_elements[element_index] : 1;
                        unique_total++;
                    } else if (!building_values) {
                        result_elements[unique_total - 1]++;
                    }
                }
                if (!building_histogram && !building_values) {
                    compact_unreferenced_arrays(parser, &arguments[0]);
                    return parse_index_postfix(parser, integer_value((long)unique_total));
                }
                compact_unreferenced_arrays(parser, NULL);
                if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }
                array = &parser->arrays[parser->array_count];
                array->element_count = unique_total;
                array->scope_depth = parser->scope_depth;
                array->id = parser->next_array_id;
                array->under_construction = 0;
                for (element_index = 0; element_index < unique_total; element_index++) {
                    array->elements[element_index] = result_elements[element_index];
                }
                value = array_value(parser->array_count, array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (strcmp(name, "min") == 0 || strcmp(name, "max") == 0 || strcmp(name, "median") == 0 || strcmp(name, "variance_sum") == 0 || strcmp(name, "mode") == 0) {
                struct ArrayValue *array;
                long selected;
                size_t element_index;
                int selecting_min = strcmp(name, "min") == 0;
                int selecting_median = strcmp(name, "median") == 0;
                int selecting_variance_sum = strcmp(name, "variance_sum") == 0;
                int selecting_mode = strcmp(name, "mode") == 0;

                if (argument_count != 1) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                array = array_from_value(parser, arguments[0]);
                if (array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (array->element_count == 0) {
                    parser->status = RUSTIC_ERR_EMPTY_ARRAY;
                    return integer_value(0);
                }
                if (selecting_median || selecting_mode) {
                    long sorted_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                    size_t scan_index;
                    for (element_index = 0; element_index < array->element_count; element_index++) {
                        sorted_elements[element_index] = array->elements[element_index];
                    }
                    for (element_index = 1; element_index < array->element_count; element_index++) {
                        long current = sorted_elements[element_index];
                        scan_index = element_index;
                        while (scan_index > 0 && sorted_elements[scan_index - 1] > current) {
                            sorted_elements[scan_index] = sorted_elements[scan_index - 1];
                            scan_index--;
                        }
                        sorted_elements[scan_index] = current;
                    }
                    if (selecting_mode) {
                        size_t best_count = 1;
                        size_t current_count = 1;
                        selected = sorted_elements[0];
                        for (element_index = 1; element_index < array->element_count; element_index++) {
                            if (sorted_elements[element_index] == sorted_elements[element_index - 1]) {
                                current_count++;
                            } else {
                                current_count = 1;
                            }
                            if (current_count > best_count) {
                                best_count = current_count;
                                selected = sorted_elements[element_index];
                            }
                        }
                    } else if (array->element_count % 2 == 1) {
                        selected = sorted_elements[array->element_count / 2];
                    } else {
                        size_t upper_index = array->element_count / 2;
                        selected = (sorted_elements[upper_index - 1] + sorted_elements[upper_index]) / 2;
                    }
                    compact_unreferenced_arrays(parser, &arguments[0]);
                    return parse_index_postfix(parser, integer_value(selected));
                }
                if (selecting_variance_sum) {
                    long mean;
                    long total = 0;
                    long variance_total = 0;
                    for (element_index = 0; element_index < array->element_count; element_index++) {
                        total += array->elements[element_index];
                    }
                    mean = total / (long)array->element_count;
                    for (element_index = 0; element_index < array->element_count; element_index++) {
                        long delta = array->elements[element_index] - mean;
                        variance_total += delta * delta;
                    }
                    compact_unreferenced_arrays(parser, &arguments[0]);
                    return parse_index_postfix(parser, integer_value(variance_total));
                }
                selected = array->elements[0];
                for (element_index = 1; element_index < array->element_count; element_index++) {
                    if ((selecting_min && array->elements[element_index] < selected) ||
                        (!selecting_min && array->elements[element_index] > selected)) {
                        selected = array->elements[element_index];
                    }
                }
                return parse_index_postfix(parser, integer_value(selected));
            }

            if (strcmp(name, "set") == 0) {
                struct ArrayValue *source_array;
                struct ArrayValue *rebuilt_array;
                long set_index;
                long set_value;

                if (argument_count != 3) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                source_array = array_from_value(parser, arguments[0]);
                if (source_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &set_index) ||
                    !value_as_integer(parser, arguments[2], &set_value)) {
                    return integer_value(0);
                }
                if (set_index < 0 || (size_t)set_index >= source_array->element_count) {
                    parser->status = RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS;
                    return integer_value(0);
                }

                compact_unreferenced_arrays(parser, &arguments[0]);
                if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }
                source_array = array_from_value(parser, arguments[0]);
                if (source_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                rebuilt_array = &parser->arrays[parser->array_count];
                *rebuilt_array = *source_array;
                rebuilt_array->scope_depth = parser->scope_depth;
                rebuilt_array->id = parser->next_array_id;
                rebuilt_array->under_construction = 0;
                rebuilt_array->elements[set_index] = set_value;
                value = array_value(parser->array_count, rebuilt_array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (strcmp(name, "push") == 0) {
                struct ArrayValue *source_array;
                struct ArrayValue *rebuilt_array;
                long pushed_value;

                if (argument_count != 2) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                source_array = array_from_value(parser, arguments[0]);
                if (source_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (!value_as_integer(parser, arguments[1], &pushed_value)) {
                    return integer_value(0);
                }
                if (source_array->element_count >= RUSTIC_MAX_ARRAY_ELEMENTS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }

                compact_unreferenced_arrays(parser, &arguments[0]);
                if (parser->array_count >= RUSTIC_MAX_ARRAYS) {
                    parser->status = RUSTIC_ERR_TOO_MANY_BINDINGS;
                    return integer_value(0);
                }
                source_array = array_from_value(parser, arguments[0]);
                if (source_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                rebuilt_array = &parser->arrays[parser->array_count];
                *rebuilt_array = *source_array;
                rebuilt_array->scope_depth = parser->scope_depth;
                rebuilt_array->id = parser->next_array_id;
                rebuilt_array->under_construction = 0;
                rebuilt_array->elements[rebuilt_array->element_count] = pushed_value;
                rebuilt_array->element_count++;
                value = array_value(parser->array_count, rebuilt_array->id);
                parser->array_count++;
                parser->next_array_id++;
                return parse_index_postfix(parser, value);
            }

            if (lookup_binding(parser, name, &value)) {
                function = function_from_value(parser, value);
                if (function == NULL) {
                    parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
                    return integer_value(0);
                }
            } else {
                function = lookup_function(parser, name);
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
            saved_loop_depth = parser->loop_depth;
            saved_loop_control = parser->loop_control;
            parser->loop_depth = 0;
            parser->loop_control = LOOP_CONTROL_NONE;
            push_scope(parser);
            for (index = 0; index < argument_count; index++) {
                add_binding(parser, function->parameters[index], arguments[index]);
                if (parser->status != RUSTIC_OK) {
                    pop_scope(parser);
                    parser->cursor = call_return;
                    parser->loop_depth = saved_loop_depth;
                    parser->loop_control = saved_loop_control;
                    return integer_value(0);
                }
            }
            value = parse_statement_sequence(parser, '}');
            if (parser->status != RUSTIC_OK) {
                pop_scope(parser);
                parser->cursor = call_return;
                parser->loop_depth = saved_loop_depth;
                parser->loop_control = saved_loop_control;
                return integer_value(0);
            }
            skip_spaces(parser);
            if (parser->cursor != function->body_end) {
                parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
                pop_scope(parser);
                parser->cursor = call_return;
                parser->loop_depth = saved_loop_depth;
                parser->loop_control = saved_loop_control;
                return integer_value(0);
            }
            pop_scope_preserving_value(parser, &value);
            parser->cursor = call_return;
            parser->loop_depth = saved_loop_depth;
            parser->loop_control = saved_loop_control;
            return parse_index_postfix(parser, value);
        }
        if (!lookup_binding(parser, name, &value)) {
            function = lookup_function(parser, name);
            if (function == NULL) {
                parser->status = RUSTIC_ERR_UNDEFINED_IDENTIFIER;
                return integer_value(0);
            }
            value = function_value((size_t)(function - parser->functions), function->id);
        }
        return parse_index_postfix(parser, value);
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
        if (*parser->cursor != '*' && *parser->cursor != '/' && *parser->cursor != '%') {
            return value;
        }
        if (!value_as_integer(parser, value, &left)) {
            return integer_value(0);
        }
        if (*parser->cursor == '*') {
            parser->cursor++;
            value = parse_factor(parser);
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, value, &right)) {
                return integer_value(0);
            }
            value = integer_value(left * right);
            continue;
        }

        if (*parser->cursor == '/') {
            parser->cursor++;
            value = parse_factor(parser);
            if (parser->status != RUSTIC_OK || !value_as_integer(parser, value, &right)) {
                return integer_value(0);
            }
            if (right == 0) {
                parser->status = RUSTIC_ERR_DIVISION_BY_ZERO;
                return integer_value(0);
            }
            value = integer_value(left / right);
            continue;
        }

        parser->cursor++;
        value = parse_factor(parser);
        if (parser->status != RUSTIC_OK || !value_as_integer(parser, value, &right)) {
            return integer_value(0);
        }
        if (right == 0) {
            parser->status = RUSTIC_ERR_DIVISION_BY_ZERO;
            return integer_value(0);
        }
        value = integer_value(left % right);
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

static struct Value parse_comparison_expression(struct Parser *parser) {
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

static int skip_logical_and_operand(struct Parser *parser);
static int skip_expression_operand(struct Parser *parser);

static int skip_index_postfix(struct Parser *parser) {
    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (*parser->cursor != '[') {
            return 1;
        }
        parser->cursor++;
        if (!skip_expression_operand(parser)) {
            return 0;
        }
        skip_spaces(parser);
        if (*parser->cursor != ']') {
            parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACKET;
            return 0;
        }
        parser->cursor++;
    }
    return 1;
}

static int skip_factor_expression(struct Parser *parser) {
    char name[RUSTIC_MAX_IDENTIFIER_LENGTH + 1];

    skip_spaces(parser);
    if (*parser->cursor == '!') {
        parser->cursor++;
        return skip_factor_expression(parser);
    }
    if (*parser->cursor == '{') {
        return skip_block(parser) && skip_index_postfix(parser);
    }
    if (cursor_starts_keyword(parser, "if")) {
        parser->cursor += 2;
        if (!skip_expression_operand(parser)) {
            return 0;
        }
        skip_spaces(parser);
        if (!skip_block(parser)) {
            return 0;
        }
        skip_spaces(parser);
        if (!cursor_starts_keyword(parser, "else")) {
            parser->status = RUSTIC_ERR_EXPECTED_IDENTIFIER;
            return 0;
        }
        parser->cursor += 4;
        return skip_block(parser) && skip_index_postfix(parser);
    }
    if (cursor_starts_keyword(parser, "match")) {
        parser->cursor += 5;
        if (!skip_expression_operand(parser)) {
            return 0;
        }
        skip_spaces(parser);
        return skip_block(parser) && skip_index_postfix(parser);
    }
    if (*parser->cursor == '[') {
        parser->cursor++;
        skip_spaces(parser);
        if (*parser->cursor != ']') {
            while (parser->status == RUSTIC_OK) {
                if (!skip_expression_operand(parser)) {
                    return 0;
                }
                skip_spaces(parser);
                if (*parser->cursor != ',') {
                    break;
                }
                parser->cursor++;
                skip_spaces(parser);
            }
        }
        if (*parser->cursor != ']') {
            parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACKET;
            return 0;
        }
        parser->cursor++;
        return skip_index_postfix(parser);
    }
    if (*parser->cursor == '(') {
        parser->cursor++;
        if (!skip_expression_operand(parser)) {
            return 0;
        }
        skip_spaces(parser);
        if (*parser->cursor != ')') {
            parser->status = RUSTIC_ERR_EXPECTED_CLOSING_PAREN;
            return 0;
        }
        parser->cursor++;
        return skip_index_postfix(parser);
    }
    if (isdigit((unsigned char)*parser->cursor)) {
        while (isdigit((unsigned char)*parser->cursor)) {
            parser->cursor++;
        }
        return skip_index_postfix(parser);
    }
    if (is_identifier_start(*parser->cursor)) {
        if (!parse_identifier(parser, name, sizeof(name))) {
            return 0;
        }
        skip_spaces(parser);
        if (*parser->cursor == '(') {
            parser->cursor++;
            skip_spaces(parser);
            while (*parser->cursor != ')') {
                if (!skip_expression_operand(parser)) {
                    return 0;
                }
                skip_spaces(parser);
                if (*parser->cursor != ',') {
                    break;
                }
                parser->cursor++;
                skip_spaces(parser);
            }
            if (*parser->cursor != ')') {
                parser->status = RUSTIC_ERR_EXPECTED_CLOSING_PAREN;
                return 0;
            }
            parser->cursor++;
        }
        return skip_index_postfix(parser);
    }

    parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
    return 0;
}

static int skip_term_expression(struct Parser *parser) {
    if (!skip_factor_expression(parser)) {
        return 0;
    }
    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (*parser->cursor != '*' && *parser->cursor != '/' && *parser->cursor != '%') {
            return 1;
        }
        parser->cursor++;
        if (!skip_factor_expression(parser)) {
            return 0;
        }
    }
    return 1;
}

static int skip_additive_expression(struct Parser *parser) {
    if (!skip_term_expression(parser)) {
        return 0;
    }
    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (*parser->cursor != '+' && *parser->cursor != '-') {
            return 1;
        }
        parser->cursor++;
        if (!skip_term_expression(parser)) {
            return 0;
        }
    }
    return 1;
}

static int skip_comparison_expression(struct Parser *parser) {
    if (!skip_additive_expression(parser)) {
        return 0;
    }
    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if ((parser->cursor[0] == '=' && parser->cursor[1] == '=') ||
            (parser->cursor[0] == '!' && parser->cursor[1] == '=') ||
            (parser->cursor[0] == '<' && parser->cursor[1] == '=') ||
            (parser->cursor[0] == '>' && parser->cursor[1] == '=')) {
            parser->cursor += 2;
        } else if (*parser->cursor == '<' || *parser->cursor == '>') {
            parser->cursor++;
        } else {
            return 1;
        }
        if (!skip_additive_expression(parser)) {
            return 0;
        }
    }
    return 1;
}

static int skip_logical_and_operand(struct Parser *parser) {
    if (!skip_comparison_expression(parser)) {
        return 0;
    }
    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (parser->cursor[0] != '&' || parser->cursor[1] != '&') {
            return 1;
        }
        parser->cursor += 2;
        if (!skip_comparison_expression(parser)) {
            return 0;
        }
    }
    return 1;
}

static int skip_expression_operand(struct Parser *parser) {
    if (!skip_logical_and_operand(parser)) {
        return 0;
    }
    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (parser->cursor[0] != '|' || parser->cursor[1] != '|') {
            return 1;
        }
        parser->cursor += 2;
        if (!skip_logical_and_operand(parser)) {
            return 0;
        }
    }
    return 1;
}

static struct Value parse_logical_and_expression(struct Parser *parser) {
    long left;
    long right;
    struct Value value = parse_comparison_expression(parser);
    struct Value right_value;

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (parser->cursor[0] != '&' || parser->cursor[1] != '&') {
            if (*parser->cursor == '&') {
                parser->status = RUSTIC_ERR_EXPECTED_OPERATOR;
                return integer_value(0);
            }
            return value;
        }

        if (!value_as_integer(parser, value, &left)) {
            return integer_value(0);
        }
        parser->cursor += 2;
        if (left == 0) {
            if (!skip_comparison_expression(parser)) {
                return integer_value(0);
            }
            value = integer_value(0);
            continue;
        }

        right_value = parse_comparison_expression(parser);
        if (parser->status != RUSTIC_OK || !value_as_integer(parser, right_value, &right)) {
            return integer_value(0);
        }
        value = integer_value(right != 0 ? 1 : 0);
    }

    return value;
}

static struct Value parse_expression(struct Parser *parser) {
    long left;
    long right;
    struct Value value = parse_logical_and_expression(parser);
    struct Value right_value;

    while (parser->status == RUSTIC_OK) {
        skip_spaces(parser);
        if (parser->cursor[0] != '|' || parser->cursor[1] != '|') {
            if (*parser->cursor == '|') {
                parser->status = RUSTIC_ERR_EXPECTED_OPERATOR;
                return integer_value(0);
            }
            return value;
        }

        if (!value_as_integer(parser, value, &left)) {
            return integer_value(0);
        }
        parser->cursor += 2;
        if (left != 0) {
            if (!skip_logical_and_operand(parser)) {
                return integer_value(0);
            }
            value = integer_value(1);
            continue;
        }

        right_value = parse_logical_and_expression(parser);
        if (parser->status != RUSTIC_OK || !value_as_integer(parser, right_value, &right)) {
            return integer_value(0);
        }
        value = integer_value(right != 0 ? 1 : 0);
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
    compact_unreferenced_arrays(parser, &value);
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
    function->id = parser->next_function_id;
    parser->next_function_id++;
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
    compact_unreferenced_arrays(parser, &value);
    *out_value = value;
    return 1;
}

static void parse_loop_control_statement(struct Parser *parser, enum LoopControl control) {
    if (control == LOOP_CONTROL_BREAK) {
        parser->cursor += 5;
    } else {
        parser->cursor += 8;
    }

    if (parser->loop_depth == 0) {
        parser->status = RUSTIC_ERR_LOOP_CONTROL_OUTSIDE_LOOP;
        return;
    }

    skip_spaces(parser);
    if (*parser->cursor != ';') {
        parser->status = RUSTIC_ERR_EXPECTED_SEMICOLON;
        return;
    }
    parser->cursor++;
    parser->loop_control = control;
}

static int skip_to_sequence_terminator(struct Parser *parser, char terminator) {
    size_t block_depth = 0;

    if (terminator == '\0') {
        return 1;
    }

    while (*parser->cursor != '\0') {
        if (block_depth == 0 && *parser->cursor == terminator) {
            return 1;
        }
        if (*parser->cursor == '{') {
            block_depth++;
        } else if (*parser->cursor == '}') {
            if (block_depth == 0) {
                return 1;
            }
            block_depth--;
        }
        parser->cursor++;
    }

    parser->status = RUSTIC_ERR_EXPECTED_CLOSING_BRACE;
    return 0;
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

        if (cursor_starts_keyword(parser, "break")) {
            parse_loop_control_statement(parser, LOOP_CONTROL_BREAK);
            saw_statement = 1;
            if (parser->status == RUSTIC_OK && !skip_to_sequence_terminator(parser, terminator)) {
                return integer_value(0);
            }
            return value;
        }

        if (cursor_starts_keyword(parser, "continue")) {
            parse_loop_control_statement(parser, LOOP_CONTROL_CONTINUE);
            saw_statement = 1;
            if (parser->status == RUSTIC_OK && !skip_to_sequence_terminator(parser, terminator)) {
                return integer_value(0);
            }
            return value;
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
        if (parser->loop_control != LOOP_CONTROL_NONE) {
            if (!skip_to_sequence_terminator(parser, terminator)) {
                return integer_value(0);
            }
            return value;
        }

        skip_spaces(parser);
        if (*parser->cursor != ';') {
            return value;
        }
        parser->cursor++;
        compact_unreferenced_arrays(parser, NULL);
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
    parser.next_function_id = 1;
    parser.array_count = 0;
    parser.next_array_id = 1;
    parser.steps_remaining = RUSTIC_MAX_STEPS;
    parser.loop_depth = 0;
    parser.loop_control = LOOP_CONTROL_NONE;
    parser.array_roots = NULL;
    parser.array_root_count = 0;
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
    case RUSTIC_ERR_DIVISION_BY_ZERO:
        return "division by zero";
    case RUSTIC_ERR_LOOP_CONTROL_OUTSIDE_LOOP:
        return "loop control outside loop";
    case RUSTIC_ERR_NO_MATCHING_MATCH_ARM:
        return "no matching match arm";
    case RUSTIC_ERR_EXPECTED_CLOSING_BRACKET:
        return "expected closing bracket";
    case RUSTIC_ERR_ARRAY_INDEX_OUT_OF_BOUNDS:
        return "array index out of bounds";
    case RUSTIC_ERR_EXPECTED_ARRAY:
        return "expected array";
    case RUSTIC_ERR_EMPTY_ARRAY:
        return "empty array";
    case RUSTIC_ERR_ARRAY_LENGTH_MISMATCH:
        return "array length mismatch";
    default:
        return "unknown rustic interpreter error";
    }
}
