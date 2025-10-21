# finder.py - contains the search heuristics and HTTP helpers
from typing import List, Optional, Set
import re
from urllib.parse import urlparse, urlunparse
import requests
from bs4 import BeautifulSoup

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "simple-search-agent/1.1",
    "Accept-Language": "en-US,en;q=0.9"
})
TIMEOUT = 6.0

BLACKLIST_SUBSTR: Set[str] = {
    "wikipedia.org",
    "facebook.com",
    "linkedin.com",
    "instagram.com",
    "twitter.com",
    "youtube.com",
    "tripadvisor.com",
    "glassdoor.com",
    "yelp.com",
    "crunchbase.com",
    "amazon.com",
    "etsy.com",
    "pinterest.com",
    "medium.com",
    "wikidata.org",
    "wikia.org",
    "web.archive.org",
}

_STOPWORDS = {"the", "and", "of", "for", "in", "on", "to", "a"}


def normalize_root(url: str) -> Optional[str]:
    if not url:
        return None
    parsed = urlparse(url, scheme="https")
    netloc = parsed.netloc or parsed.path
    if not netloc:
        return None
    scheme = parsed.scheme if parsed.scheme else "https"
    root = urlunparse((scheme, netloc, "", "", "", ""))
    return root.rstrip("/")


def get_domain(url: str) -> str:
    p = urlparse(url)
    domain = p.netloc.lower()
    if domain.startswith("www."):
        return domain[4:]
    return domain


def is_blacklisted(domain: str) -> bool:
    d = domain.lower()
    for bad in BLACKLIST_SUBSTR:
        if bad in d:
            return True
    return False


def duckduckgo_html_search(query: str, max_results: int = 8) -> List[str]:
    url = "https://html.duckduckgo.com/html/"
    try:
        r = SESSION.post(url, data={"q": query}, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for a in soup.select("a.result__a")[:max_results]:
        href = a.get("href")
        if href:
            results.append(href)
    if not results:
        for a in soup.find_all("a", href=True)[:max_results]:
            href = str(a['href'])
            if href and href.startswith("http"):
                results.append(href)
    seen = set()
    out = []
    for u in results:
        root = normalize_root(u)
        if not root:
            continue
        if root not in seen:
            seen.add(root)
            out.append(root)
    return out


def check_url_alive(url: str) -> bool:
    """Quick check: does the URL respond with a successful HTML page?"""
    try:
        r = SESSION.head(url, timeout=4, allow_redirects=True)
        if r.status_code in (405, 403):
            r = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True)
        if 200 <= r.status_code < 400:
            return True
    except Exception:
        return False
    return False


def slug_candidates(name: str) -> List[str]:
    base = re.sub(r"\(.*?\)", "", name).strip()
    tokens = re.findall(r"[A-Za-z0-9]+", base)
    if not tokens:
        return []
    joined = "".join(tokens).lower()
    first = tokens[0].lower()
    guesses = []
    if joined:
        guesses.append(joined)
    if first and first != joined:
        guesses.append(first)
    if len(tokens) > 1:
        guesses.append("-".join([t.lower() for t in tokens]))
    seen = set(); out=[]
    for g in guesses:
        if g not in seen:
            seen.add(g); out.append(g)
    return out


def _extract_query_tokens(q: str) -> List[str]:
    """Return meaningful tokens from the query (lowercased), filtering stopwords.

    Tokens of length >=2 are considered useful. Single-letter queries ("A", "I")
    are kept only if they are common acronyms (handled by being length 1 but present).
    """
    raw = re.findall(r"[A-Za-z0-9]+", q.lower())
    toks = [t for t in raw if t not in _STOPWORDS]
    return toks


def find_official_url(name: str) -> Optional[str]:
    """Main routine: always verifies URLs and attempts to avoid unrelated matches.

    Heuristics:
    - Extract tokens from the query; if there are *no* reasonable tokens (e.g. query
      is pure punctuation), return None early.
    - Prefer search results whose domain contains at least one query token of length>=2
      (or any token if query is short).
    - Only return a candidate if it responds to HTTP checks.
    """
    q = name.strip()
    if not q:
        return None
    tokens = _extract_query_tokens(q)
    if not tokens:
        return None

    candidates = duckduckgo_html_search(q, max_results=12)

    for root in candidates:
        domain = get_domain(root)
        if is_blacklisted(domain):
            continue
        if "/wiki/" in root:
            continue
        if not any((t in domain) for t in tokens if len(t) >= 2 or len(tokens) == 1):
            continue
        if check_url_alive(root):
            return root

    for slug in slug_candidates(q):
        for candidate in (f"https://{slug}.com", f"https://www.{slug}.com", f"https://{slug}.org", f"https://{slug}.net"):
            domain = get_domain(candidate)
            if is_blacklisted(domain):
                continue
            if not any((t in domain) for t in tokens if len(t) >= 2 or len(tokens) == 1):
                continue
            if check_url_alive(candidate):
                return candidate

    return None
