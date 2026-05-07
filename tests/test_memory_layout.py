import pytest

from r_project import vector_layout
from r_project.memory import (
    ByteSpan,
    MemoryField,
    filter_byte_spans,
    find_overlapping_byte_spans,
    flatten_byte_spans,
    group_byte_span_overlap_totals,
    group_byte_span_overlaps,
    leaf_byte_spans,
    layout_field,
    render_byte_span_overlaps,
    render_grouped_byte_span_overlap_totals,
    render_grouped_byte_span_overlaps,
    render_layout,
    struct_layout,
)


def test_vector_layout_pads_payload_start_and_total_size_to_alignment():
    layout = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)

    assert layout.data_offset == 4
    assert layout.element_offsets == [4, 8]
    assert layout.total_size == 12
    assert layout.padding_after_header == 1
    assert layout.trailing_padding == 0


def test_struct_layout_aligns_field_offsets_and_tail_padding():
    layout = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1),
            MemoryField(name="count", size=4, alignment=4),
        ]
    )

    assert [field.offset for field in layout.fields] == [0, 4]
    assert layout.fields[1].leading_padding == 3
    assert layout.total_size == 8
    assert layout.alignment == 4
    assert layout.tail_padding == 0


def test_struct_layout_rounds_total_size_for_struct_arrays():
    layout = struct_layout(
        [
            MemoryField(name="count", size=4, alignment=4),
            MemoryField(name="tag", size=1, alignment=1),
        ]
    )

    assert [field.offset for field in layout.fields] == [0, 4]
    assert layout.total_size == 8
    assert layout.alignment == 4
    assert layout.tail_padding == 3


def test_struct_layout_can_nest_struct_layouts_as_fields():
    header = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1),
            MemoryField(name="count", size=4, alignment=4),
        ]
    )

    layout = struct_layout(
        [
            MemoryField(name="prefix", size=1, alignment=1),
            layout_field("header", header),
        ]
    )

    assert layout.fields[1].size == 8
    assert layout.fields[1].alignment == 4
    assert layout.fields[1].offset == 4
    assert layout.fields[1].leading_padding == 3
    assert layout.total_size == 12


def test_struct_layout_can_nest_vector_layouts_as_fields():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)

    layout = struct_layout(
        [
            MemoryField(name="prefix", size=1, alignment=1),
            layout_field("payload", payload),
        ]
    )

    assert layout.fields[1].size == 12
    assert layout.fields[1].alignment == 4
    assert layout.fields[1].offset == 4
    assert layout.total_size == 16


def test_render_layout_names_struct_fields_offsets_and_padding():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
    layout = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1),
            layout_field("payload", payload),
        ]
    )

    assert render_layout("packet", layout) == "\n".join(
        [
            "packet: struct size=16 align=4 tail_padding=0",
            "  tag @ 0 size=1 align=1 leading_padding=0",
            "  payload @ 4 size=12 align=4 leading_padding=3",
        ]
    )


def test_render_layout_names_vector_offsets_and_padding():
    layout = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)

    assert render_layout("payload", layout) == "\n".join(
        [
            "payload: vector size=12 element_size=4 align=4 length=2",
            "  header size=3 padding_after_header=1 data_offset=4",
            "  element[0] @ 4 stride=4",
            "  element[1] @ 8 stride=4",
            "  trailing_padding=0",
        ]
    )


def test_struct_layout_preserves_symbolic_field_tags_in_rendered_memory_maps():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
    layout = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1, tags=("source:token-kind",)),
            layout_field("payload", payload, tags=("source:literal-bytes", "runtime:vector")),
        ]
    )

    assert layout.fields[0].tags == ("source:token-kind",)
    assert layout.fields[1].tags == ("source:literal-bytes", "runtime:vector")
    assert render_layout("packet", layout) == "\n".join(
        [
            "packet: struct size=16 align=4 tail_padding=0",
            "  tag @ 0 size=1 align=1 leading_padding=0 tags=source:token-kind",
            "  payload @ 4 size=12 align=4 leading_padding=3 tags=source:literal-bytes,runtime:vector",
        ]
    )


def test_render_layout_can_expand_nested_tagged_layouts_for_traceability():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
    header = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1, tags=("source:token-kind",)),
            MemoryField(name="count", size=4, alignment=4, tags=("source:length",)),
        ]
    )
    packet = struct_layout(
        [
            layout_field("header", header, tags=("runtime:header",)),
            layout_field("payload", payload, tags=("source:literal-bytes", "runtime:vector")),
        ]
    )

    assert packet.fields[0].layout is header
    assert packet.fields[1].layout is payload
    assert render_layout("packet", packet, include_nested=True) == "\n".join(
        [
            "packet: struct size=20 align=4 tail_padding=0",
            "  header @ 0 size=8 align=4 leading_padding=0 tags=runtime:header",
            "    header: struct size=8 align=4 tail_padding=0",
            "      tag @ 0 size=1 align=1 leading_padding=0 tags=source:token-kind",
            "      count @ 4 size=4 align=4 leading_padding=3 tags=source:length",
            "  payload @ 8 size=12 align=4 leading_padding=0 tags=source:literal-bytes,runtime:vector",
            "    payload: vector size=12 element_size=4 align=4 length=2",
            "      header size=3 padding_after_header=1 data_offset=4",
            "      element[0] @ 4 stride=4",
            "      element[1] @ 8 stride=4",
            "      trailing_padding=0",
        ]
    )


def test_layout_byte_spans_summarize_tagged_runtime_ranges():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
    packet = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1, tags=("source:token-kind",)),
            layout_field("payload", payload, tags=("source:literal-bytes", "runtime:vector")),
        ]
    )

    spans = packet.byte_spans()

    assert [(span.name, span.start, span.end, span.size, span.tags) for span in spans] == [
        ("tag", 0, 1, 1, ("source:token-kind",)),
        ("payload", 4, 16, 12, ("source:literal-bytes", "runtime:vector")),
    ]


def test_render_layout_can_include_byte_span_summaries_on_demand():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
    layout = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1, tags=("source:token-kind",)),
            layout_field("payload", payload, tags=("source:literal-bytes",)),
        ]
    )

    assert render_layout("packet", layout, include_spans=True) == "\n".join(
        [
            "packet: struct size=16 align=4 tail_padding=0",
            "  tag @ 0 size=1 align=1 leading_padding=0 tags=source:token-kind span=0..1",
            "  payload @ 4 size=12 align=4 leading_padding=3 tags=source:literal-bytes span=4..16",
        ]
    )


def test_flatten_byte_spans_qualifies_nested_child_ranges_for_overlap_checks():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
    header = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1, tags=("source:token-kind",)),
            MemoryField(name="count", size=4, alignment=4, tags=("source:length",)),
        ]
    )
    packet = struct_layout(
        [
            layout_field("header", header, tags=("runtime:header",)),
            layout_field("payload", payload, tags=("source:literal-bytes", "runtime:vector")),
        ]
    )

    spans = flatten_byte_spans("packet", packet)

    assert [(span.name, span.start, span.end, span.tags) for span in spans] == [
        ("packet.header", 0, 8, ("runtime:header",)),
        ("packet.header.tag", 0, 1, ("runtime:header", "source:token-kind")),
        ("packet.header.count", 4, 8, ("runtime:header", "source:length")),
        ("packet.payload", 8, 20, ("source:literal-bytes", "runtime:vector")),
        ("packet.payload.header", 8, 11, ("source:literal-bytes", "runtime:vector")),
        ("packet.payload.element[0]", 12, 16, ("source:literal-bytes", "runtime:vector")),
        ("packet.payload.element[1]", 16, 20, ("source:literal-bytes", "runtime:vector")),
    ]


def test_filter_byte_spans_selects_flattened_ranges_by_name_and_tags():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
    header = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1, tags=("source:token-kind",)),
            MemoryField(name="count", size=4, alignment=4, tags=("source:length",)),
        ]
    )
    packet = struct_layout(
        [
            layout_field("header", header, tags=("runtime:header",)),
            layout_field("payload", payload, tags=("source:literal-bytes", "runtime:vector")),
        ]
    )
    spans = flatten_byte_spans("packet", packet)

    filtered = filter_byte_spans(spans, name_prefix="packet.payload.", tags_all=("runtime:vector",))

    assert [(span.name, span.start, span.end, span.tags) for span in filtered] == [
        ("packet.payload.header", 8, 11, ("source:literal-bytes", "runtime:vector")),
        ("packet.payload.element[0]", 12, 16, ("source:literal-bytes", "runtime:vector")),
        ("packet.payload.element[1]", 16, 20, ("source:literal-bytes", "runtime:vector")),
    ]


def test_filter_byte_spans_supports_name_contains_and_any_tag_predicates():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
    packet = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1, tags=("source:token-kind",)),
            layout_field("payload", payload, tags=("source:literal-bytes", "runtime:vector")),
        ]
    )
    spans = flatten_byte_spans("packet", packet)

    filtered = filter_byte_spans(spans, name_contains="element", tags_any=("runtime:vector", "runtime:string"))

    assert [(span.name, span.start, span.end) for span in filtered] == [
        ("packet.payload.element[0]", 8, 12),
        ("packet.payload.element[1]", 12, 16),
    ]


def test_leaf_byte_spans_suppresses_parent_container_ranges():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
    packet = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1, tags=("source:token-kind",)),
            layout_field("payload", payload, tags=("source:literal-bytes", "runtime:vector")),
        ]
    )
    spans = flatten_byte_spans("packet", packet)

    leaves = leaf_byte_spans(spans)

    assert [(span.name, span.start, span.end, span.tags) for span in leaves] == [
        ("packet.tag", 0, 1, ("source:token-kind",)),
        ("packet.payload.header", 4, 7, ("source:literal-bytes", "runtime:vector")),
        ("packet.payload.element[0]", 8, 12, ("source:literal-bytes", "runtime:vector")),
        ("packet.payload.element[1]", 12, 16, ("source:literal-bytes", "runtime:vector")),
    ]


def test_leaf_byte_spans_can_be_combined_with_filters_for_leaf_only_overlap_reports():
    payload = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)
    packet = struct_layout(
        [
            MemoryField(name="tag", size=1, alignment=1, tags=("source:token-kind",)),
            layout_field("payload", payload, tags=("source:literal-bytes", "runtime:vector")),
        ]
    )
    spans = flatten_byte_spans("packet", packet)

    leaves = leaf_byte_spans(filter_byte_spans(spans, tags_all=("runtime:vector",)))

    assert [(span.name, span.start, span.end) for span in leaves] == [
        ("packet.payload.header", 4, 7),
        ("packet.payload.element[0]", 8, 12),
        ("packet.payload.element[1]", 12, 16),
    ]


def test_find_overlapping_byte_spans_reports_intersecting_runtime_ranges():
    left_payload = vector_layout(header_size=0, element_size=4, element_alignment=4, length=2)
    right_payload = vector_layout(header_size=0, element_size=4, element_alignment=4, length=1)
    left_spans = flatten_byte_spans("left", left_payload, base_offset=16)
    right_spans = flatten_byte_spans("right", right_payload, base_offset=20)

    overlaps = find_overlapping_byte_spans(left_spans + right_spans)

    assert [(overlap.left.name, overlap.right.name, overlap.start, overlap.end, overlap.size) for overlap in overlaps] == [
        ("left.element[1]", "right.element[0]", 20, 24, 4),
    ]


def test_find_overlapping_byte_spans_does_not_report_touching_ranges():
    packet = vector_layout(header_size=0, element_size=4, element_alignment=4, length=2)

    overlaps = find_overlapping_byte_spans(flatten_byte_spans("packet", packet))

    assert overlaps == []


def test_render_byte_span_overlaps_formats_stable_human_readable_diagnostics():
    left_payload = vector_layout(header_size=0, element_size=4, element_alignment=4, length=2)
    right_payload = vector_layout(header_size=0, element_size=4, element_alignment=4, length=1)
    spans = flatten_byte_spans("left", left_payload, base_offset=16) + flatten_byte_spans("right", right_payload, base_offset=20)

    assert render_byte_span_overlaps(spans) == "\n".join(
        [
            "# Byte Span Overlaps",
            "",
            "| Left span | Right span | Overlap | Size |",
            "| --- | --- | ---: | ---: |",
            "| left.element[1] (20..24) | right.element[0] (20..24) | 20..24 | 4 |",
        ]
    )


def test_render_byte_span_overlaps_reports_empty_state_when_ranges_do_not_intersect():
    spans = flatten_byte_spans("packet", vector_layout(header_size=0, element_size=4, element_alignment=4, length=2))

    assert render_byte_span_overlaps(spans) == "# Byte Span Overlaps\n\nNo overlapping byte spans."


def test_group_byte_span_overlaps_can_group_intersections_by_provenance_tag():
    spans = [
        ByteSpan("left.value", 0, 8, tags=("source:literal", "runtime:left")),
        ByteSpan("right.value", 4, 12, tags=("source:literal", "runtime:right")),
        ByteSpan("scratch", 6, 10),
    ]

    grouped = group_byte_span_overlaps(spans, by="tag")

    assert list(grouped) == ["source:literal", "untagged"]
    assert [(overlap.left.name, overlap.right.name, overlap.start, overlap.end) for overlap in grouped["source:literal"]] == [
        ("left.value", "right.value", 4, 8),
    ]
    assert [(overlap.left.name, overlap.right.name) for overlap in grouped["untagged"]] == [
        ("left.value", "scratch"),
        ("right.value", "scratch"),
    ]


def test_group_byte_span_overlap_totals_summarize_large_reports_for_dashboards():
    spans = [
        ByteSpan("left.value", 0, 8, tags=("source:literal", "runtime:left")),
        ByteSpan("right.value", 4, 12, tags=("source:literal", "runtime:right")),
        ByteSpan("scratch", 6, 10),
    ]

    totals = group_byte_span_overlap_totals(spans, by="tag")

    assert list(totals) == ["source:literal", "untagged"]
    assert totals["source:literal"].overlap_count == 1
    assert totals["source:literal"].total_overlap_size == 4
    assert totals["untagged"].overlap_count == 2
    assert totals["untagged"].total_overlap_size == 6


def test_render_grouped_byte_span_overlap_totals_formats_compact_dashboard_table():
    spans = [
        ByteSpan("left.value", 0, 8, tags=("source:literal", "runtime:left")),
        ByteSpan("right.value", 4, 12, tags=("source:literal", "runtime:right")),
        ByteSpan("scratch", 6, 10),
    ]

    assert render_grouped_byte_span_overlap_totals(spans, by="tag") == "\n".join(
        [
            "# Byte Span Overlap Totals by Tag",
            "",
            "| Group | Overlaps | Total overlap bytes |",
            "| --- | ---: | ---: |",
            "| source:literal | 1 | 4 |",
            "| untagged | 2 | 6 |",
        ]
    )


def test_render_grouped_byte_span_overlap_totals_reports_empty_state_when_ranges_do_not_intersect():
    spans = [ByteSpan("left", 0, 4), ByteSpan("right", 4, 8)]

    assert render_grouped_byte_span_overlap_totals(spans, by="tag") == (
        "# Byte Span Overlap Totals by Tag\n\nNo overlapping byte spans."
    )


def test_render_grouped_byte_span_overlaps_can_group_intersections_by_name_prefix():
    spans = [
        ByteSpan("left.header.tag", 0, 4),
        ByteSpan("right.header.tag", 2, 6),
        ByteSpan("right.payload.element[0]", 3, 7),
    ]

    assert render_grouped_byte_span_overlaps(spans, by="name_prefix", prefix_depth=2) == "\n".join(
        [
            "# Byte Span Overlaps by Name Prefix",
            "",
            "## left.header ↔ right.header",
            "",
            "| Left span | Right span | Overlap | Size |",
            "| --- | --- | ---: | ---: |",
            "| left.header.tag (0..4) | right.header.tag (2..6) | 2..4 | 2 |",
            "",
            "## left.header ↔ right.payload",
            "",
            "| Left span | Right span | Overlap | Size |",
            "| --- | --- | ---: | ---: |",
            "| left.header.tag (0..4) | right.payload.element[0] (3..7) | 3..4 | 1 |",
            "",
            "## right.header ↔ right.payload",
            "",
            "| Left span | Right span | Overlap | Size |",
            "| --- | --- | ---: | ---: |",
            "| right.header.tag (2..6) | right.payload.element[0] (3..7) | 3..6 | 3 |",
        ]
    )


def test_vector_layout_rejects_non_power_of_two_alignment():
    with pytest.raises(ValueError, match="element_alignment must be a power of two"):
        vector_layout(header_size=0, element_size=4, element_alignment=3, length=1)


def test_struct_layout_rejects_non_power_of_two_field_alignment():
    with pytest.raises(ValueError, match="field 'packed' alignment must be a power of two"):
        struct_layout([MemoryField(name="packed", size=2, alignment=3)])


def test_vector_layout_rejects_total_size_above_explicit_limit():
    with pytest.raises(ValueError, match="vector total_size 16 exceeds max_total_size 15"):
        vector_layout(header_size=8, element_size=4, element_alignment=4, length=2, max_total_size=15)


def test_struct_layout_rejects_total_size_above_explicit_limit():
    with pytest.raises(ValueError, match="struct total_size 8 exceeds max_total_size 7"):
        struct_layout(
            [MemoryField(name="count", size=4, alignment=4), MemoryField(name="tag", size=1, alignment=1)],
            max_total_size=7,
        )
