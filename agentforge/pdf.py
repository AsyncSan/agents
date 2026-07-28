"""Markdown-to-PDF rendering for compliance artefacts.

A thin layer over ``weasyprint`` that produces A4 PDFs from the Markdown
documents emitted by the FRIA, Annex IV, and literacy modules. Print CSS
is embedded so the output looks consistent regardless of caller.

Import-time side effects are kept to a minimum; weasyprint pulls in
pango/cairo only when first used.
"""

from __future__ import annotations

import html

from markdown_it import MarkdownIt

_PRINT_CSS = """
@page {
  size: A4;
  margin: 22mm 18mm;
  @bottom-right { content: counter(page) " / " counter(pages); font-size: 9pt; color: #666; }
  @bottom-left { content: "agents.renemurrell.de"; font-size: 9pt; color: #999; }
}

body {
  font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #111;
}

h1 { font-size: 20pt; margin: 0 0 0.4em; padding-bottom: 0.3em; border-bottom: 1px solid #ddd; }
h2 { font-size: 14pt; margin: 1.4em 0 0.4em; padding-bottom: 0.15em; border-bottom: 1px solid #eee; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 1em 0 0.3em; page-break-after: avoid; }
p { margin: 0.45em 0; }
strong { color: #000; }
em { color: #333; }
hr { border: none; border-top: 1px solid #ccc; margin: 1.2em 0; }

ul, ol { margin: 0.4em 0 0.8em 1.2em; padding: 0; }
li { margin: 0.15em 0; }
li p { margin: 0.1em 0; }

code { background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt; }
pre { background: #f7f8fa; padding: 10px 12px; border-radius: 4px; overflow: auto; font-size: 9pt; border: 1px solid #e5e7eb; page-break-inside: avoid; }
pre code { background: transparent; padding: 0; }

table { width: 100%; border-collapse: collapse; margin: 0.8em 0; font-size: 9.5pt; page-break-inside: avoid; }
th, td { border: 1px solid #d8dcdf; padding: 6px 9px; text-align: left; vertical-align: top; }
th { background: #f1f3f5; font-weight: 600; }
tr:nth-child(even) td { background: #fafbfc; }

blockquote { border-left: 3px solid #94a3b8; color: #475569; margin: 0.6em 0; padding: 0.3em 0.9em; background: #f8fafc; }

a { color: #0284c7; text-decoration: none; }
"""

_md = MarkdownIt("commonmark", {"html": False, "breaks": False, "linkify": True}).enable("table")


def markdown_to_pdf(markdown: str, title: str) -> bytes:
    """Render a Markdown document to a PDF byte string."""
    from weasyprint import CSS, HTML

    body_html = _md.render(markdown)
    doc_html = (
        "<!doctype html><html><head>"
        f"<meta charset='utf-8'><title>{html.escape(title)}</title>"
        "</head><body>"
        f"{body_html}"
        "</body></html>"
    )
    return HTML(string=doc_html).write_pdf(stylesheets=[CSS(string=_PRINT_CSS)])
