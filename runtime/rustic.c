#include "rustic.h"

#include <ctype.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define RUSTIC_MAX_BINDINGS 1024
#define RUSTIC_MAX_FUNCTIONS 8
#define RUSTIC_MAX_IDENTIFIER_LENGTH 31
#define RUSTIC_MAX_ARRAYS 64
#define RUSTIC_MAX_ARRAY_ELEMENTS 16
#define RUSTIC_MAX_PARAMETERS 8
#define RUSTIC_MAX_STEPS 512

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
                        parser->array_roots = arguments;
                        parser->array_root_count = argument_count;
                        arguments[argument_count] = parse_expression(parser);
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

            if (strcmp(name, "reverse") == 0 || strcmp(name, "take") == 0) {
                struct ArrayValue *source_array;
                struct ArrayValue *result_array;
                long source_elements[RUSTIC_MAX_ARRAY_ELEMENTS];
                long take_count = 0;
                size_t source_count;
                size_t result_count;
                size_t element_index;
                int taking = strcmp(name, "take") == 0;

                if (argument_count != (taking ? 2 : 1)) {
                    parser->status = RUSTIC_ERR_WRONG_ARGUMENT_COUNT;
                    return integer_value(0);
                }
                source_array = array_from_value(parser, arguments[0]);
                if (source_array == NULL) {
                    parser->status = RUSTIC_ERR_EXPECTED_ARRAY;
                    return integer_value(0);
                }
                if (taking) {
                    if (!value_as_integer(parser, arguments[1], &take_count)) {
                        return integer_value(0);
                    }
                    if (take_count < 0) {
                        parser->status = RUSTIC_ERR_EXPECTED_INTEGER;
                        return integer_value(0);
                    }
                }

                source_count = source_array->element_count;
                for (element_index = 0; element_index < source_count; element_index++) {
                    source_elements[element_index] = source_array->elements[element_index];
                }
                if (taking && (size_t)take_count < source_count) {
                    result_count = (size_t)take_count;
                } else {
                    result_count = source_count;
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
                    if (taking) {
                        result_array->elements[element_index] = source_elements[element_index];
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

            if (strcmp(name, "min") == 0 || strcmp(name, "max") == 0) {
                struct ArrayValue *array;
                long selected;
                size_t element_index;
                int selecting_min = strcmp(name, "min") == 0;

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
    default:
        return "unknown rustic interpreter error";
    }
}
