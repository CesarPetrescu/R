import pytest

from r_project import vector_layout
from r_project.memory import MemoryField, struct_layout


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


def test_vector_layout_rejects_non_power_of_two_alignment():
    with pytest.raises(ValueError, match="element_alignment must be a power of two"):
        vector_layout(header_size=0, element_size=4, element_alignment=3, length=1)


def test_struct_layout_rejects_non_power_of_two_field_alignment():
    with pytest.raises(ValueError, match="field 'packed' alignment must be a power of two"):
        struct_layout([MemoryField(name="packed", size=2, alignment=3)])
