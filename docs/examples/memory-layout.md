# Memory-layout support example

Python support tooling, **not** an operation of the C interpreter. Run the Python block after `python3 -m pip install -e .` from the repository root. Its assertions and annotated output were previously in the project README.

Runtime layout helpers are also importable for tests or future low-level R
runtime work:

```python
from r_project import vector_layout
from r_project.memory import ByteSpan, MemoryField, filter_byte_spans, find_grouped_byte_span_overlap_total_violations, find_overlapping_byte_spans, flatten_byte_spans, group_byte_span_overlap_totals, group_byte_span_overlaps, layout_field, leaf_byte_spans, render_byte_span_overlaps, render_grouped_byte_span_overlap_threshold_violations, render_grouped_byte_span_overlap_totals, render_grouped_byte_span_overlaps, render_layout, struct_layout

payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
record = struct_layout(
    [
        MemoryField(name="tag", size=1, alignment=1),
        layout_field("payload", payload, tags=("source:literal-bytes",)),
    ]
)
assert record.fields[1].offset == 4
assert record.total_size == 16

print(render_layout("record", record, include_spans=True))
# record: struct size=16 align=4 tail_padding=0
#   tag @ 0 size=1 align=1 leading_padding=0 span=0..1
#   payload @ 4 size=12 align=4 leading_padding=3 tags=source:literal-bytes span=4..16
assert [(span.name, span.start, span.end) for span in record.byte_spans()] == [
    ("tag", 0, 1),
    ("payload", 4, 16),
]
assert [(span.name, span.start, span.end) for span in flatten_byte_spans("record", record)] == [
    ("record.tag", 0, 1),
    ("record.payload", 4, 16),
    ("record.payload.header", 4, 7),
    ("record.payload.element[0]", 8, 12),
    ("record.payload.element[1]", 12, 16),
]

assert [(span.name, span.start, span.end) for span in filter_byte_spans(leaf_byte_spans(flatten_byte_spans("record", record)), name_prefix="record.payload.", tags_all=("source:literal-bytes",))] == [
    ("record.payload.header", 4, 7),
    ("record.payload.element[0]", 8, 12),
    ("record.payload.element[1]", 12, 16),
]

left = flatten_byte_spans("left", payload, base_offset=16)
right = flatten_byte_spans("right", vector_layout(header_size=0, element_size=4, element_alignment=4, length=1), base_offset=20)
assert [(overlap.left.name, overlap.right.name, overlap.start, overlap.end) for overlap in find_overlapping_byte_spans(left + right)] == [
    ("left.element[0]", "right.element[0]", 20, 24),
]
assert render_byte_span_overlaps(left + right) == "\n".join(
    [
        "# Byte Span Overlaps",
        "",
        "| Left span | Right span | Overlap | Size |",
        "| --- | --- | ---: | ---: |",
        "| left.element[0] (20..24) | right.element[0] (20..24) | 20..24 | 4 |",
    ]
)

tagged_spans = [
    ByteSpan("left.value", 0, 8, tags=("source:literal", "runtime:left")),
    ByteSpan("right.value", 4, 12, tags=("source:literal", "runtime:right")),
    ByteSpan("scratch", 6, 10),
]
assert list(group_byte_span_overlaps(tagged_spans, by="tag")) == ["source:literal", "untagged"]
assert find_grouped_byte_span_overlap_total_violations(
    tagged_spans,
    by="tag",
    max_overlap_count=1,
    max_total_overlap_size=4,
)["untagged"].total_overlap_size == 6
assert render_grouped_byte_span_overlap_totals(tagged_spans, by="tag") == "\n".join(
    [
        "# Byte Span Overlap Totals by Tag",
        "",
        "| Group | Overlaps | Total overlap bytes |",
        "| --- | ---: | ---: |",
        "| source:literal | 1 | 4 |",
        "| untagged | 2 | 6 |",
    ]
)
assert render_grouped_byte_span_overlap_threshold_violations(
    tagged_spans,
    by="tag",
    max_overlap_count=1,
    max_total_overlap_size=4,
) == "\n".join(
    [
        "# Byte Span Overlap Threshold Violations by Tag",
        "",
        "| Group | Overlaps | Max overlaps | Total overlap bytes | Max overlap bytes | Violations |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
        "| untagged | 2 | 1 | 6 | 4 | overlap count, total overlap bytes |",
    ]
)
assert render_grouped_byte_span_overlaps(tagged_spans, by="tag") == "\n".join(
    [
        "# Byte Span Overlaps by Tag",
        "",
        "## source:literal",
        "",
        "| Left span | Right span | Overlap | Size |",
        "| --- | --- | ---: | ---: |",
        "| left.value (0..8) | right.value (4..12) | 4..8 | 4 |",
        "",
        "## untagged",
        "",
        "| Left span | Right span | Overlap | Size |",
        "| --- | --- | ---: | ---: |",
        "| left.value (0..8) | scratch (6..10) | 6..8 | 2 |",
        "| right.value (4..12) | scratch (6..10) | 6..10 | 4 |",
    ]
)

layout = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
assert layout.data_offset == 4
assert layout.element_offsets == [4, 8]
assert layout.total_size == 12

# Optional runtime bounds fail explicitly instead of silently exceeding a
# caller-provided byte-size limit.
vector_layout(header_size=8, element_size=4, element_alignment=4, length=2, max_total_size=16)
```
