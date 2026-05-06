"""Repository readiness reporting and runtime helpers for project R."""

from .memory import (
    ByteSpan,
    MemoryField,
    PlacedField,
    StructLayout,
    VectorLayout,
    flatten_byte_spans,
    layout_field,
    render_layout,
    struct_layout,
    vector_layout,
)
from .report import ProjectReport, analyze_project

__all__ = [
    "ByteSpan",
    "MemoryField",
    "PlacedField",
    "ProjectReport",
    "StructLayout",
    "VectorLayout",
    "analyze_project",
    "flatten_byte_spans",
    "layout_field",
    "render_layout",
    "struct_layout",
    "vector_layout",
]
