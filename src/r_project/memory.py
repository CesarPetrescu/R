from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryField:
    """Input field description for byte-oriented memory layout."""

    name: str
    size: int
    alignment: int
    tags: tuple[str, ...] = ()
    layout: StructLayout | VectorLayout | None = None


@dataclass(frozen=True)
class PlacedField:
    """A field after layout, including explicit padding before it."""

    name: str
    size: int
    alignment: int
    offset: int
    leading_padding: int
    tags: tuple[str, ...] = ()
    layout: StructLayout | VectorLayout | None = None


@dataclass(frozen=True)
class ByteSpan:
    """Half-open byte range for quick memory-map overlap checks."""

    name: str
    start: int
    end: int
    tags: tuple[str, ...] = ()

    @property
    def size(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class ByteSpanOverlap:
    """Intersection between two half-open byte spans."""

    left: ByteSpan
    right: ByteSpan
    start: int
    end: int

    @property
    def size(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class StructLayout:
    """C-like structure layout with internal and tail padding made explicit."""

    fields: list[PlacedField]
    total_size: int
    alignment: int
    tail_padding: int

    def byte_spans(self, *, base_offset: int = 0) -> list[ByteSpan]:
        """Return half-open byte ranges for fields in this struct layout."""

        return [
            ByteSpan(name=field.name, start=base_offset + field.offset, end=base_offset + field.offset + field.size, tags=field.tags)
            for field in self.fields
        ]


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

    def byte_spans(self, *, base_offset: int = 0) -> list[ByteSpan]:
        """Return half-open byte ranges for the vector header and elements."""

        spans = [ByteSpan(name="header", start=base_offset, end=base_offset + self.header_size)]
        spans.extend(
            ByteSpan(name=f"element[{index}]", start=base_offset + offset, end=base_offset + offset + self.element_size)
            for index, offset in enumerate(self.element_offsets)
        )
        return spans


def layout_field(name: str, layout: StructLayout | VectorLayout, *, tags: tuple[str, ...] = ()) -> MemoryField:
    """Return a structure field for embedding an already computed layout.
    This lets callers compose low-level object layouts from smaller struct or
    vector layouts while preserving the nested object's size and alignment.
    Optional symbolic tags attach source-level provenance to rendered maps.
    """

    if isinstance(layout, StructLayout):
        return MemoryField(name=name, size=layout.total_size, alignment=layout.alignment, tags=tags, layout=layout)
    if isinstance(layout, VectorLayout):
        return MemoryField(name=name, size=layout.total_size, alignment=layout.element_alignment, tags=tags, layout=layout)
    raise TypeError("layout must be a StructLayout or VectorLayout")


def flatten_byte_spans(name: str, layout: StructLayout | VectorLayout, *, base_offset: int = 0) -> list[ByteSpan]:
    """Return qualified half-open byte ranges for a layout and its children.

    Struct fields and vector parts are named relative to ``name``. When a
    struct field embeds another layout, the field span is included first and
    then child spans are emitted with absolute offsets and inherited tags so
    overlap diagnostics can compare nested runtime ranges directly.
    """

    return _flatten_byte_span_items(name, layout, base_offset=base_offset, inherited_tags=())


def _flatten_byte_span_items(
    name: str, layout: StructLayout | VectorLayout, *, base_offset: int, inherited_tags: tuple[str, ...]
) -> list[ByteSpan]:
    if isinstance(layout, StructLayout):
        spans: list[ByteSpan] = []
        for field in layout.fields:
            field_name = f"{name}.{field.name}"
            field_start = base_offset + field.offset
            field_tags = inherited_tags + field.tags
            spans.append(ByteSpan(name=field_name, start=field_start, end=field_start + field.size, tags=field_tags))
            if field.layout is not None:
                spans.extend(
                    _flatten_byte_span_items(field_name, field.layout, base_offset=field_start, inherited_tags=field_tags)
                )
        return spans
    if isinstance(layout, VectorLayout):
        return [
            ByteSpan(name=f"{name}.{span.name}", start=span.start, end=span.end, tags=inherited_tags)
            for span in layout.byte_spans(base_offset=base_offset)
        ]
    raise TypeError("layout must be a StructLayout or VectorLayout")


def find_overlapping_byte_spans(spans: list[ByteSpan]) -> list[ByteSpanOverlap]:
    """Return pairwise intersections for half-open byte spans.

    Ranges that only touch at an endpoint are not overlaps. Results are stable:
    spans are compared in ascending start/end/name order and each pair appears
    once with the earlier span as ``left``.
    """

    ordered_spans = sorted(spans, key=lambda span: (span.start, span.end, span.name))
    overlaps: list[ByteSpanOverlap] = []
    for left_index, left in enumerate(ordered_spans):
        for right in ordered_spans[left_index + 1 :]:
            if right.start >= left.end:
                break
            overlap_start = max(left.start, right.start)
            overlap_end = min(left.end, right.end)
            if overlap_start < overlap_end:
                overlaps.append(ByteSpanOverlap(left=left, right=right, start=overlap_start, end=overlap_end))
    return overlaps


def render_byte_span_overlaps(spans: list[ByteSpan]) -> str:
    """Render stable Markdown diagnostics for overlapping byte spans."""

    overlaps = find_overlapping_byte_spans(spans)
    if not overlaps:
        return "# Byte Span Overlaps\n\nNo overlapping byte spans."
    lines = [
        "# Byte Span Overlaps",
        "",
        "| Left span | Right span | Overlap | Size |",
        "| --- | --- | ---: | ---: |",
    ]
    lines.extend(
        f"| {_render_overlap_endpoint(overlap.left)} | {_render_overlap_endpoint(overlap.right)} | "
        f"{overlap.start}..{overlap.end} | {overlap.size} |"
        for overlap in overlaps
    )
    return "\n".join(lines)


def _render_overlap_endpoint(span: ByteSpan) -> str:
    return f"{span.name} ({span.start}..{span.end})"


def render_layout(
    name: str, layout: StructLayout | VectorLayout, *, include_nested: bool = False, include_spans: bool = False
) -> str:
    """Render a named memory layout as stable, line-oriented debug text."""

    return "\n".join(_render_layout_lines(name, layout, include_nested=include_nested, include_spans=include_spans, indent=0))


def _render_layout_lines(
    name: str, layout: StructLayout | VectorLayout, *, include_nested: bool, include_spans: bool, indent: int
) -> list[str]:
    prefix = " " * indent
    if isinstance(layout, StructLayout):
        lines = [f"{prefix}{name}: struct size={layout.total_size} align={layout.alignment} tail_padding={layout.tail_padding}"]
        for field in layout.fields:
            lines.append(
                f"{prefix}  {field.name} @ {field.offset} size={field.size} align={field.alignment} "
                f"leading_padding={field.leading_padding}{_render_tags(field.tags)}{_render_span(field.offset, field.size, include_spans)}"
            )
            if include_nested and field.layout is not None:
                lines.extend(
                    _render_layout_lines(field.name, field.layout, include_nested=True, include_spans=include_spans, indent=indent + 4)
                )
        return lines
    if isinstance(layout, VectorLayout):
        lines = [
            f"{prefix}{name}: vector size={layout.total_size} element_size={layout.element_size} "
            f"align={layout.element_alignment} length={layout.length}",
            f"{prefix}  header size={layout.header_size} padding_after_header={layout.padding_after_header} "
            f"data_offset={layout.data_offset}",
        ]
        lines.extend(
            f"{prefix}  element[{index}] @ {offset} stride={layout.element_stride}{_render_span(offset, layout.element_size, include_spans)}"
            for index, offset in enumerate(layout.element_offsets)
        )
        lines.append(f"{prefix}  trailing_padding={layout.trailing_padding}")
        return lines
    raise TypeError("layout must be a StructLayout or VectorLayout")


def _render_tags(tags: tuple[str, ...]) -> str:
    if not tags:
        return ""
    return f" tags={','.join(tags)}"


def _render_span(offset: int, size: int, include_spans: bool) -> str:
    if not include_spans:
        return ""
    return f" span={offset}..{offset + size}"


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
                tags=field.tags,
                layout=field.layout,
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
