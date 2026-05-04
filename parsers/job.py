import requests
from bs4 import BeautifulSoup


def fetch_job_from_url(url: str) -> dict:
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except Exception as e:
        raise ValueError(f"Failed to fetch URL: {e}") from e

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("title")
    job_title = title_tag.get_text(strip=True) if title_tag else ""

    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    body = soup.find("body")
    job_description = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)

    if not job_description.strip():
        raise ValueError("No job description content found at URL")

    return {
        "job_title": job_title,
        "company": "",
        "job_description": job_description,
    }
