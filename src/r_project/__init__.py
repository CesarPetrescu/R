"""Repository readiness reporting and runtime helpers for project R."""

from .memory import VectorLayout, vector_layout
from .report import ProjectReport, analyze_project

__all__ = ["ProjectReport", "VectorLayout", "analyze_project", "vector_layout"]
