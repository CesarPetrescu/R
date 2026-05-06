"""Repository readiness reporting and runtime helpers for project R."""

from .memory import (
    ByteSpan,
    ByteSpanOverlap,
    MemoryField,
    PlacedField,
    StructLayout,
    VectorLayout,
    filter_byte_spans,
    find_overlapping_byte_spans,
    flatten_byte_spans,
    group_byte_span_overlaps,
    leaf_byte_spans,
    layout_field,
    render_byte_span_overlaps,
    render_grouped_byte_span_overlaps,
    render_layout,
    struct_layout,
    vector_layout,
)
from .report import ProjectReport, analyze_project

__all__ = [
    "ByteSpan",
    "ByteSpanOverlap",
    "MemoryField",
    "PlacedField",
    "ProjectReport",
    "StructLayout",
    "VectorLayout",
    "analyze_project",
    "filter_byte_spans",
    "find_overlapping_byte_spans",
    "flatten_byte_spans",
    "group_byte_span_overlaps",
    "leaf_byte_spans",
    "layout_field",
    "render_byte_span_overlaps",
    "render_grouped_byte_span_overlaps",
    "render_layout",
    "struct_layout",
    "vector_layout",
]
