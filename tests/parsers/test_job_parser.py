import pytest
from unittest.mock import patch, MagicMock
from parsers.job import fetch_job_from_url


def _mock_response(html: str, status: int = 200):
    mock = MagicMock()
    mock.text = html
    mock.status_code = status
    mock.raise_for_status = MagicMock()
    return mock


JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{"@type":"JobPosting","title":"Staff Engineer","description":"<p>Build things at scale.</p>",
 "hiringOrganization":{"@type":"Organization","name":"Acme"}}
</script>
</head><body><p>Loading...</p></body></html>
"""

META_HTML = """
<html><head>
<meta property="og:title" content="Senior Engineer at Acme"/>
<meta property="og:description" content="We are looking for a senior engineer to join our platform team and build scalable systems."/>
</head><body></body></html>
"""

PLAIN_HTML = """
<html><head><title>Backend Engineer - Acme</title></head>
<body><h1>Backend Engineer</h1><p>We need an experienced backend engineer to build
our distributed systems. You will work with Python, AWS, and Kubernetes every day.
Requirements: 5+ years experience, strong Python skills, cloud experience.</p></body></html>
"""


def test_js_site_raises_immediately():
    with pytest.raises(ValueError, match="paste"):
        fetch_job_from_url("https://apply.workable.com/acme/j/ABC123/")


def test_js_site_greenhouse_raises():
    with pytest.raises(ValueError, match="paste"):
        fetch_job_from_url("https://boards.greenhouse.io/acme/jobs/123")


def test_jsonld_extracted():
    with patch("requests.get", return_value=_mock_response(JSONLD_HTML)):
        result = fetch_job_from_url("https://example.com/jobs/1")
    assert result["job_title"] == "Staff Engineer"
    assert result["company"] == "Acme"
    assert "Build things at scale" in result["job_description"]


def test_meta_fallback():
    with patch("requests.get", return_value=_mock_response(META_HTML)):
        result = fetch_job_from_url("https://example.com/jobs/1")
    assert result["job_title"] == "Senior Engineer at Acme"
    assert "senior engineer" in result["job_description"]


def test_plain_html_fallback():
    with patch("requests.get", return_value=_mock_response(PLAIN_HTML)):
        result = fetch_job_from_url("https://example.com/jobs/1")
    assert "Backend Engineer" in result["job_title"]
    assert "Python" in result["job_description"]


def test_empty_page_raises():
    with patch("requests.get", return_value=_mock_response("<html><body></body></html>")):
        with pytest.raises(ValueError, match="paste"):
            fetch_job_from_url("https://example.com/jobs/1")


def test_fetch_error_raises():
    with patch("requests.get", side_effect=Exception("timeout")):
        with pytest.raises(ValueError, match="Failed to fetch"):
            fetch_job_from_url("https://example.com/jobs/1")
