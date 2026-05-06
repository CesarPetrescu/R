"""Repository readiness reporting and runtime helpers for project R."""

from .memory import MemoryField, PlacedField, StructLayout, VectorLayout, struct_layout, vector_layout
from .report import ProjectReport, analyze_project

__all__ = [
    "MemoryField",
    "PlacedField",
    "ProjectReport",
    "StructLayout",
    "VectorLayout",
    "analyze_project",
    "struct_layout",
    "vector_layout",
]
