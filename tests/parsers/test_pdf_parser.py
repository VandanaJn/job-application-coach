import pytest
from unittest.mock import patch, MagicMock


def test_extracts_text_from_pdf():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "John Doe\nSoftware Engineer\n5 years experience"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        from parsers.pdf import extract_text
        result = extract_text(b"fake pdf bytes")

    assert "Software Engineer" in result


def test_concatenates_text_from_multiple_pages():
    pages = []
    for text in ["Page one content.", "Page two content."]:
        page = MagicMock()
        page.extract_text.return_value = text
        pages.append(page)
    mock_reader = MagicMock()
    mock_reader.pages = pages

    with patch("pypdf.PdfReader", return_value=mock_reader):
        from parsers.pdf import extract_text
        result = extract_text(b"fake pdf bytes")

    assert "Page one content." in result
    assert "Page two content." in result


def test_raises_value_error_when_no_text_extracted():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        from parsers.pdf import extract_text
        with pytest.raises(ValueError, match="no text"):
            extract_text(b"fake pdf bytes")


def test_raises_value_error_on_invalid_pdf():
    with patch("pypdf.PdfReader", side_effect=Exception("not a pdf")):
        from parsers.pdf import extract_text
        with pytest.raises(ValueError, match="invalid"):
            extract_text(b"not a pdf")
