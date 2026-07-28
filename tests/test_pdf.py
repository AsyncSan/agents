"""Smoke tests for the PDF renderer."""

from agentforge.pdf import markdown_to_pdf


def test_rendering_returns_pdf_bytes():
    pdf = markdown_to_pdf("# Title\n\nBody.", title="Demo")
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 500


def test_rendering_tables_and_lists():
    md = """# Compliance

## Items

- one
- two

| A | B |
|---|---|
| 1 | 2 |
"""
    pdf = markdown_to_pdf(md, title="Tables")
    assert pdf[:5] == b"%PDF-"


def test_rendering_escapes_title():
    pdf = markdown_to_pdf("# x", title="<script>alert(1)</script>")
    assert pdf[:5] == b"%PDF-"
