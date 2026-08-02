from app.ingestion.chunking import chunk_markdown, chunk_text


def test_chunking_preserves_document_metadata() -> None:
    chunks = chunk_markdown(
        "# Travel\nSubmit receipts within 30 days.",
        title="expense-policy",
        department="Finance",
    )
    assert chunks[0].title == "expense-policy"
    assert chunks[0].department == "Finance"
    assert "Submit receipts" in chunks[0].content


def test_chunking_splits_by_heading() -> None:
    chunks = chunk_markdown(
        "# Section 1\nContent A.\n\n## Subsection\nContent B.\n\n# Section 2\nContent C.",
        title="test",
        department="General",
    )
    assert len(chunks) >= 2
    sections = [c.section for c in chunks]
    assert "Section 1" in sections


def test_chunking_splits_long_content() -> None:
    long_para = "Long content. " * 200  # ~2,400 chars
    chunks = chunk_markdown(
        f"# Topic\n{long_para}",
        title="test",
        max_size=800,
        overlap=120,
    )
    assert len(chunks) >= 3  # 2,400 / 800 ≈ 3 chunks
    for c in chunks:
        assert len(c.content) <= 800


def test_overlap_preserves_context() -> None:
    text = "A B C D E F G H I J K L M N O P Q R S T U V W X Y Z " * 50
    chunks = chunk_markdown(
        text, title="test",
        max_size=200,
        overlap=50,
    )
    assert len(chunks) >= 2


def test_chunk_text_preserves_pdf_page_metadata() -> None:
    chunks = chunk_text(
        "住宿报销上限为每晚 800 元。",
        title="travel-policy",
        section="第 3 页",
        source_type="pdf",
        source_path="data/documents/travel-policy.pdf",
        page_number=3,
    )
    assert len(chunks) == 1
    assert chunks[0].source_type == "pdf"
    assert chunks[0].source_path == "data/documents/travel-policy.pdf"
    assert chunks[0].page_number == 3
    assert chunks[0].content_type == "text"

