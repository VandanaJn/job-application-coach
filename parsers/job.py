import json
import requests
from bs4 import BeautifulSoup

_HEADERS = {"User-Agent": "Mozilla/5.0"}

_JS_SITE_HINTS = [
    "workable.com", "greenhouse.io", "lever.co", "ashbyhq.com",
    "myworkdayjobs.com", "icims.com", "smartrecruiters.com",
]

_PASTE_ERROR = (
    "Could not extract job description from this URL — the site likely requires "
    "JavaScript to render. Please paste the job description text directly instead."
)


def fetch_job_from_url(url: str) -> dict:
    if any(hint in url for hint in _JS_SITE_HINTS):
        raise ValueError(_PASTE_ERROR)

    try:
        response = requests.get(url, timeout=10, headers=_HEADERS)
        response.raise_for_status()
    except Exception as e:
        raise ValueError(f"Failed to fetch URL: {e}") from e

    soup = BeautifulSoup(response.text, "html.parser")

    # Try JSON-LD JobPosting schema first (most reliable)
    result = _extract_jsonld(soup)
    if result:
        return result

    # Try og:description / meta description as fallback
    result = _extract_meta(soup, url)
    if result:
        return result

    # Plain HTML extraction
    result = _extract_html(soup, url)
    if result:
        return result

    raise ValueError(_PASTE_ERROR)


def _extract_jsonld(soup: BeautifulSoup) -> dict | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            # Handle single object or @graph array
            items = data if isinstance(data, list) else data.get("@graph", [data])
            for item in items:
                if item.get("@type") == "JobPosting":
                    description = item.get("description", "")
                    if description:
                        return {
                            "job_title": item.get("title", ""),
                            "company": _nested(item, "hiringOrganization", "name") or "",
                            "job_description": BeautifulSoup(description, "html.parser").get_text("\n", strip=True),
                        }
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def _extract_meta(soup: BeautifulSoup, url: str) -> dict | None:
    desc = (
        _meta_content(soup, "property", "og:description")
        or _meta_content(soup, "name", "description")
    )
    if not desc or len(desc) < 50:
        return None
    title = _meta_content(soup, "property", "og:title") or ""
    return {"job_title": title, "company": "", "job_description": desc}


def _extract_html(soup: BeautifulSoup, url: str) -> dict | None:
    title_tag = soup.find("title")
    job_title = title_tag.get_text(strip=True) if title_tag else ""

    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    body = soup.find("body")
    text = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)

    if len(text) < 200:
        return None

    return {"job_title": job_title, "company": "", "job_description": text}


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str:
    tag = soup.find("meta", attrs={attr: value})
    return tag.get("content", "").strip() if tag else ""


def _nested(data: dict, *keys: str) -> str:
    for key in keys:
        if not isinstance(data, dict):
            return ""
        data = data.get(key, {})
    return data if isinstance(data, str) else ""
