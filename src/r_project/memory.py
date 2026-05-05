from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryField:
    """Input field description for byte-oriented memory layout."""

    name: str
    size: int
    alignment: int


@dataclass(frozen=True)
class PlacedField:
    """A field after layout, including explicit padding before it."""

    name: str
    size: int
    alignment: int
    offset: int
    leading_padding: int


@dataclass(frozen=True)
class StructLayout:
    """C-like structure layout with internal and tail padding made explicit."""

    fields: list[PlacedField]
    total_size: int
    alignment: int
    tail_padding: int


def struct_layout(fields: list[MemoryField]) -> StructLayout:
    """Lay out structure fields with field alignment and struct tail padding.

    Fields are placed in order. Each field offset is rounded up to that field's
    alignment, and the final structure size is rounded up to the maximum field
    alignment so arrays of the structure keep every element correctly aligned.
    """

    placed_fields: list[PlacedField] = []
    offset = 0
    struct_alignment = 1
    for field in fields:
        _validate_field(field)
        aligned_offset = _align_up(offset, field.alignment)
        placed_fields.append(
            PlacedField(
                name=field.name,
                size=field.size,
                alignment=field.alignment,
                offset=aligned_offset,
                leading_padding=aligned_offset - offset,
            )
        )
        offset = aligned_offset + field.size
        struct_alignment = max(struct_alignment, field.alignment)

    total_size = _align_up(offset, struct_alignment)
    return StructLayout(
        fields=placed_fields,
        total_size=total_size,
        alignment=struct_alignment,
        tail_padding=total_size - offset,
    )


def _align_up(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment


def _validate_field(field: MemoryField) -> None:
    if field.size <= 0:
        raise ValueError(f"field {field.name!r} size must be positive")
    if field.alignment <= 0:
        raise ValueError(f"field {field.name!r} alignment must be positive")
