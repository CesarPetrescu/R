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


@dataclass(frozen=True)
class VectorLayout:
    header_size: int
    element_size: int
    element_alignment: int
    length: int
    data_offset: int
    element_stride: int
    element_offsets: list[int]
    total_size: int

    @property
    def padding_after_header(self) -> int:
        return self.data_offset - self.header_size

    @property
    def trailing_padding(self) -> int:
        payload_end = self.data_offset + (self.element_stride * self.length)
        return self.total_size - payload_end


def struct_layout(fields: list[MemoryField], *, max_total_size: int | None = None) -> StructLayout:
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
        aligned_offset = align_up(offset, field.alignment)
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

    total_size = align_up(offset, struct_alignment)
    _enforce_max_total_size("struct", total_size, max_total_size)
    return StructLayout(
        fields=placed_fields,
        total_size=total_size,
        alignment=struct_alignment,
        tail_padding=total_size - offset,
    )


def vector_layout(
    *, header_size: int, element_size: int, element_alignment: int, length: int, max_total_size: int | None = None
) -> VectorLayout:
    """Return byte offsets for a vector payload with alignment padding included."""
    _require_non_negative("header_size", header_size)
    _require_positive("element_size", element_size)
    _require_positive("element_alignment", element_alignment)
    _require_power_of_two("element_alignment", element_alignment)
    _require_non_negative("length", length)

    data_offset = align_up(header_size, element_alignment)
    element_stride = align_up(element_size, element_alignment)
    element_offsets = [data_offset + (index * element_stride) for index in range(length)]
    total_size = align_up(data_offset + (element_stride * length), element_alignment)
    _enforce_max_total_size("vector", total_size, max_total_size)
    return VectorLayout(
        header_size=header_size,
        element_size=element_size,
        element_alignment=element_alignment,
        length=length,
        data_offset=data_offset,
        element_stride=element_stride,
        element_offsets=element_offsets,
        total_size=total_size,
    )


def align_up(value: int, alignment: int) -> int:
    _require_non_negative("value", value)
    _require_positive("alignment", alignment)
    remainder = value % alignment
    if remainder == 0:
        return value
    return value + alignment - remainder


def _validate_field(field: MemoryField) -> None:
    if field.size <= 0:
        raise ValueError(f"field {field.name!r} size must be positive")
    if field.alignment <= 0:
        raise ValueError(f"field {field.name!r} alignment must be positive")
    _require_power_of_two(f"field {field.name!r} alignment", field.alignment)


def _require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _require_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _require_power_of_two(name: str, value: int) -> None:
    if value & (value - 1) != 0:
        raise ValueError(f"{name} must be a power of two")


def _enforce_max_total_size(kind: str, total_size: int, max_total_size: int | None) -> None:
    if max_total_size is None:
        return
    _require_non_negative("max_total_size", max_total_size)
    if total_size > max_total_size:
        raise ValueError(f"{kind} total_size {total_size} exceeds max_total_size {max_total_size}")
