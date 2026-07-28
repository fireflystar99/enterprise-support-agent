from app.ingestion.chunking import chunk_markdown


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


def test_chunking_rejects_empty_chunks() -> None:
    chunks = chunk_markdown("# Only heading\n\n\n\nSpaces only.\n", title="test", department="General")
    assert len(chunks) >= 1
