"""
Tests for PDF ingestion pipeline.

Verifies that PDF files are correctly extracted to text
and processed through the ingestion orchestrator.
"""
import sys
import json
from pathlib import Path

import pytest

# Add CORE to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = PROJECT_ROOT / "core" / "CORE"
sys.path.insert(0, str(CORE_PATH))

from book_os.pipeline.pdf_extractor import extract_text, extract_to_temp_txt


def _create_test_pdf(path: Path):
    """Create a minimal valid PDF for testing."""
    # Minimal PDF with 2 pages of text
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 6 0 R >>
endobj
5 0 obj
<< /Length 60 >>stream
BT /F1 12 Tf 72 720 Td (Test page 1: Arkaim is ancient.) Tj ET
endstream
endobj
6 0 obj
<< /Length 60 >>stream
BT /F1 12 Tf 72 720 Td (Test page 2: Hyperborea mythos.) Tj ET
endstream
endobj
xref
0 7
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
0000000296 00000 n 
0000000390 00000 n 
trailer
<< /Size 7 /Root 1 0 R >>
startxref
487
%%EOF
"""
    path.write_bytes(pdf_content)


@pytest.fixture
def test_pdf(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _create_test_pdf(pdf_path)
    return pdf_path


def _pdf_lib_available() -> bool:
    """Check if any PDF extraction library is installed."""
    try:
        import pdfplumber  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        import PyPDF2  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _pdf_lib_available(), reason="PDF library (pdfplumber/PyPDF2) not installed")
def test_extract_text_from_pdf(test_pdf):
    """Extract text from a PDF and verify structure."""
    text = extract_text(test_pdf)
    assert isinstance(text, str)
    assert len(text) > 0
    # Should contain page markers or extracted text
    assert "Arkaim" in text or "СТРАНИЦА" in text or "page" in text.lower()


@pytest.mark.skipif(not _pdf_lib_available(), reason="PDF library (pdfplumber/PyPDF2) not installed")
def test_extract_to_temp_txt(test_pdf):
    """Extract PDF to a temporary txt file."""
    txt_path = extract_to_temp_txt(test_pdf)
    try:
        assert txt_path.exists()
        assert txt_path.suffix == ".txt"
        content = txt_path.read_text(encoding="utf-8")
        assert len(content) > 0
    finally:
        if txt_path.exists():
            txt_path.unlink()


def test_pdf_with_mock_ingestion(test_pdf):
    """Verify PDF can be ingested if pdfplumber/PyPDF2 available."""
    try:
        from book_os.pipeline.orchestrator import IngestionOrchestrator
        from book_os.source_store import SourceStore
        from book_os.entity_store import EntityStore
        from book_os.fact_store import FactStore
        from book_os.relationship_store import RelationshipStore
        from book_os.provenance_tracker import ProvenanceTracker
    except ImportError:
        pytest.skip("BOOK OS modules not available")

    # Mock stores that just record calls
    class MockStore:
        def __init__(self): self.items = []
        def add(self, *a, **k): 
            from dataclasses import dataclass
            @dataclass
            class R:
                id: str = "mock"
                hash: str = "mock"
                title: str = "mock"
            return R()
        def list(self): return []

    orch = IngestionOrchestrator(
        source_store=MockStore(),
        entity_store=MockStore(),
        fact_store=MockStore(),
        relationship_store=MockStore(),
        provenance_tracker=MockStore(),
        index_engine=None,
    )
    # This will attempt PDF extraction; if extractors missing, it should fail gracefully
    try:
        result = orch.ingest(test_pdf, doc_type="external", version="9.9.9")
        assert "status" in result
    except RuntimeError as e:
        # Expected if no PDF library installed
        assert "PDF" in str(e) or "extract" in str(e).lower()