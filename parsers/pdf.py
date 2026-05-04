import io
import pypdf


def extract_text(pdf_bytes: bytes) -> str:
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:
        raise ValueError(f"invalid PDF: {e}") from e

    text = "\n".join(
        page.extract_text() or "" for page in reader.pages
    ).strip()

    if not text:
        raise ValueError("no text extracted from PDF")

    return text
