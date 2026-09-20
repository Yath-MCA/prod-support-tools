from core.extraction_run_paths import format_extraction_run_folder_name


def test_timestamp_prefix_then_extraction():
    name = format_extraction_run_folder_name(
        "20260919_234603", "BITS", "ext-link_ext-link-type_doi"
    )
    assert name == "20260919_234603_extraction_BITS_ext-link_ext-link-type_doi"
    assert name.startswith("20260919_234603_extraction_")
