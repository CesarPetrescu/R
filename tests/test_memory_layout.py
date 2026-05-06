from r_project import vector_layout


def test_vector_layout_pads_payload_start_and_total_size_to_alignment():
    layout = vector_layout(header_size=3, element_size=4, element_alignment=4, length=2)

    assert layout.data_offset == 4
    assert layout.element_offsets == [4, 8]
    assert layout.total_size == 12
    assert layout.padding_after_header == 1
    assert layout.trailing_padding == 0
