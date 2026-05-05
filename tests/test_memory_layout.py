from r_project.memory import MemoryField, struct_layout


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
