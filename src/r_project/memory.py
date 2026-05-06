from __future__ import annotations

from dataclasses import dataclass


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


def vector_layout(*, header_size: int, element_size: int, element_alignment: int, length: int) -> VectorLayout:
    """Return byte offsets for a vector payload with alignment padding included."""
    _require_non_negative("header_size", header_size)
    _require_positive("element_size", element_size)
    _require_positive("element_alignment", element_alignment)
    _require_non_negative("length", length)

    data_offset = align_up(header_size, element_alignment)
    element_stride = align_up(element_size, element_alignment)
    element_offsets = [data_offset + (index * element_stride) for index in range(length)]
    total_size = align_up(data_offset + (element_stride * length), element_alignment)
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


def _require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _require_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")
