import requests
from bs4 import BeautifulSoup
from typing import Iterable, Any

# shared session (connection reuse)
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


# -------------------------
# CMS DETECTORS
# -------------------------

def detect_wordpress(
    soup: BeautifulSoup | None,
    html: str,
    headers: dict[str, Any],
    cookies: Iterable[Any]
    ) -> tuple[int, list[str]]:
    """
    Detect whether a website is likely running WordPress based on common indicators.

    The function analyzes HTML content, parsed DOM, HTTP headers, and cookies to
    compute a confidence score and collect evidence pointing to WordPress usage.

    Scoring rules:
    - Meta generator tag containing "WordPress": +5
    - Presence of "/wp-content/" in HTML: +3
    - Presence of "wp-emoji" in HTML: +2
    - HTTP headers containing "WordPress": +2
    - Cookies containing "WordPress" in their name: +3

    Args:
        soup (bs4.BeautifulSoup | None): Parsed HTML document. If None, DOM-based
            checks are skipped.
        html (str): Raw HTML content of the page.
        headers (dict | Any): HTTP response headers.
        cookies (Iterable[Any]): Cookies returned by the HTTP response. Each cookie
            is expected to have a `name` attribute.

    Returns:
        tuple[int, list[str]]: A tuple containing:
            - score: An integer confidence score indicating likelihood of WordPress.
            - evidence: A list of strings identifying which indicators were detected.
    """
    score = 0
    evidence = []

    if soup:
        gen = soup.find("meta", attrs={"name": "generator"})
        if gen and "wordpress" in gen.get("content", "").lower():
            score += 5
            evidence.append("meta_generator")

    if "/wp-content/" in html:
        score += 3
        evidence.append("wp-content")

    if "wp-emoji" in html:
        score += 2
        evidence.append("wp-emoji")

    if "wordpress" in str(headers).lower():
        score += 2
        evidence.append("headers")

    if any("wordpress" in c.name.lower() for c in cookies):
        score += 3
        evidence.append("cookies")

    return score, evidence


def detect_shopify(
    soup: BeautifulSoup | None,
    html: str,
    headers: dict[str, Any],
    cookies: Iterable[Any]
    ) -> tuple[int, list[str]]:
    """
    Detect whether a website is likely running Shopify based on common indicators.

    The function inspects HTML content, parsed DOM, HTTP headers, and cookies to
    compute a confidence score and collect evidence suggesting Shopify usage.

    Scoring rules:
    - References to Shopify CDN (cdn.shopify.com): +5
    - Presence of Shopify JavaScript globals (shopify.theme, shopify.routes): +3
    - Meta generator tag containing "Shopify": +4
    - Cart or checkout paths in HTML (/cart or /checkout): +2
    - HTTP headers containing "Shopify": +2
    - Cookies starting with "_shopify": +3 (first match only)

    Args:
        soup (bs4.BeautifulSoup | None): Parsed HTML document. If None, DOM-based
            checks are skipped.
        html (str): Raw HTML content of the page.
        headers (dict | Any): HTTP response headers.
        cookies (Iterable[Any]): Cookies returned by the HTTP response. Each cookie
            is expected to have a `name` attribute.

    Returns:
        tuple[int, list[str]]: A tuple containing:
            - score: An integer confidence score indicating likelihood of Shopify.
            - evidence: A list of strings describing which indicators were detected.
    """
    score = 0
    evidence = []

    html_lower = html.lower()
    headers_lower = str(headers).lower()

    if "cdn.shopify.com" in html_lower:
        score += 5
        evidence.append("cdn.shopify.com")

    if "shopify.theme" in html_lower or "shopify.routes" in html_lower:
        score += 3
        evidence.append("shopify_js_globals")

    if soup:
        meta_gen = soup.find("meta", attrs={"name": "generator"})
        if meta_gen and "shopify" in meta_gen.get("content", "").lower():
            score += 4
            evidence.append("meta_generator")

    if "/cart" in html_lower or "/checkout" in html_lower:
        score += 2
        evidence.append("cart_or_checkout_path")

    if "shopify" in headers_lower:
        score += 2
        evidence.append("headers")

    for cookie in cookies:
        if cookie.name.startswith("_shopify"):
            score += 3
            evidence.append(f"cookie:{cookie.name}")
            break

    return score, evidence


def detect_wix(
    soup: BeautifulSoup | None,
    html: str,
    headers: dict[str, Any],
    cookies: Iterable[Any]
    ) -> tuple[int, list[str]]:
    """
    Detect whether a website is likely running Wix based on common indicators.

    The function evaluates HTML content, parsed DOM, HTTP headers, and cookies
    to compute a confidence score and collect evidence suggesting Wix usage.

    Scoring rules:
    - References to Wix static assets (wixstatic.com): +5
    - Meta generator tag containing "Wix": +4
    - Presence of Wix JavaScript globals (e.g., wixbi, __wix): +3
    - Presence of Wix-specific data attributes (data-wix-*): +3
    - HTTP headers containing "Wix": +2
    - Cookies starting with "wix": +3 (first match only)

    Args:
        soup (bs4.BeautifulSoup | None): Parsed HTML document. If None, DOM-based
            checks are skipped.
        html (str): Raw HTML content of the page.
        headers (dict | Any): HTTP response headers.
        cookies (Iterable[Any]): Cookies returned by the HTTP response. Each cookie
            is expected to have a `name` attribute.

    Returns:
        tuple[int, list[str]]: A tuple containing:
            - score: An integer confidence score indicating likelihood of Wix.
            - evidence: A list of strings describing which indicators were detected.
    """
    score = 0
    evidence = []

    html_lower = html.lower()
    headers_lower = str(headers).lower()

    if "wixstatic.com" in html_lower:
        score += 5
        evidence.append("wixstatic.com")

    if soup:
        meta_gen = soup.find("meta", attrs={"name": "generator"})
        if meta_gen and "wix" in meta_gen.get("content", "").lower():
            score += 4
            evidence.append("meta_generator")

    wix_js_signals = [
        "wixbi",
        "wixcodesdk",
        "__wix",
        "wixexperiments"
    ]

    if any(signal in html_lower for signal in wix_js_signals):
        score += 3
        evidence.append("wix_js_globals")

    if "data-wix-" in html_lower:
        score += 3
        evidence.append("data_wix_attributes")

    if "wix" in headers_lower:
        score += 2
        evidence.append("headers")

    for cookie in cookies:
        if cookie.name.lower().startswith("wix"):
            score += 3
            evidence.append(f"cookie:{cookie.name}")
            break

    return score, evidence


# -------------------------
# CMS SCRAPER
# -------------------------

CMSDetectionResult = tuple[str, float, list[str]]
DetectionScore = tuple[int, list[str]]

def detect_cms(url: str, timeout: int = 5) -> CMSDetectionResult:
    """
    Fetch a website and attempt to identify its content management system (CMS).

    The function retrieves the target URL, applies fast heuristics for common CMS
    platforms, and falls back to CMS-specific detection functions to compute a
    confidence score and supporting evidence.

    Detection flow:
    - Perform HTTP GET request
    - Apply early-exit checks for strong Shopify or Wix indicators
    - Parse HTML only if meta tags are present
    - Run CMS detectors (WordPress, Shopify, Wix)
    - Select CMS with highest confidence score

    Args:
        url (str): URL of the website to analyze.
        timeout (int, optional): Request timeout in seconds. Defaults to 5.

    Returns:
        tuple[str, float, list[str]]: A tuple containing:
            - cms: Detected CMS name ("wordpress", "shopify", "wix", or "unknown")
            - confidence: Confidence score between 0.0 and 1.0
            - evidence: List of strings indicating which signals were detected
    """
    try:
        resp = session.get(url, timeout=timeout)

        html = resp.text
        html_lower = html.lower()
        headers = resp.headers
        cookies = resp.cookies

        # early exit
        if "cdn.shopify.com" in html_lower:
            return "shopify", 0.9, ["cdn.shopify.com"]

        if "wixstatic.com" in html_lower:
            return "wix", 0.9, ["wixstatic.com"]

        # Parse only if needed
        soup = BeautifulSoup(html, "html.parser") \
            if "<meta" in html_lower else None

        scores: dict[str, DetectionScore] = {}

        scores["wordpress"] = detect_wordpress(
            soup, html, headers, cookies
        )
        scores["shopify"] = detect_shopify(
            soup, html, headers, cookies
        )
        scores["wix"] = detect_wix(
            soup, html, headers, cookies
        )

        cms, (score, evidence) = max(
            scores.items(),
            key=lambda x: x[1][0]
        )

        if score < 3:
            return "unknown", 0.0, []

        confidence = min(score / 10, 1.0)
        return cms, confidence, evidence

    except Exception:
        return "unknown", 0.0, []
