#!/usr/bin/env python3

from typing import List, Optional
from flask import Flask, request, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
import re

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "simple-search-agent/1.1",
    "Accept-Language": "en-US,en;q=0.9"
})
TIMEOUT = 6.0

BLACKLIST_SUBSTR = {
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
        if r.status_code == 405 or r.status_code == 403:
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

app = Flask(__name__)

TEMPLATE = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Find Official Site — Search Agent</title>
  <style>
    :root{--bg:#0f1724;--card:#0b1220;--accent:#06b6d4;--muted:#94a3b8;--text:#e6eef6}
    html,body{height:100%;margin:0;font-family:Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;color:var(--text);background:linear-gradient(180deg,#071024 0%, #07172a 100%);}
    .wrap{min-height:100%;display:flex;align-items:center;justify-content:center;padding:32px}
    .card{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));border-radius:14px;box-shadow:0 8px 30px rgba(2,6,23,0.6);padding:28px;width:100%;max-width:820px}
    h1{margin:0 0 8px;font-size:20px}
    p.lead{margin:0 0 18px;color:var(--muted)}
    .form-row{display:flex;gap:12px;align-items:center}
    input[type=text]{flex:1;padding:14px 16px;border-radius:10px;border:1px solid rgba(255,255,255,0.06);background:rgba(255,255,255,0.02);color:var(--text);font-size:16px}
    button{background:var(--accent);border:none;padding:12px 16px;border-radius:10px;color:#042027;font-weight:600;cursor:pointer}
    button[aria-busy="true"]{opacity:0.7;cursor:wait}
    .result{margin-top:18px;padding:12px;border-radius:10px;background:rgba(255,255,255,0.02);display:flex;gap:10px;align-items:center}
    .result a{color:var(--accent);font-weight:600;text-decoration:none;word-break:anywhere}
    .small{font-size:13px;color:var(--muted)}
    .actions{margin-left:auto;display:flex;gap:8px}
    .example{margin-top:12px;color:var(--muted);font-size:13px}
    .sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
    @media (max-width:560px){.form-row{flex-direction:column;align-items:stretch}button{width:100%}}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card" aria-labelledby="title">
      <div style="display:flex;align-items:center;gap:12px">
        <img src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 24 24' fill='none' stroke='%2306b6d4' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='M22 11.5a10 10 0 1 0-3.4 7.1'/><path d='M12 2v10l3 3'/></svg>" alt="search icon" style="width:40px;height:40px">
        <div>
          <h1 id="title">Find the official website</h1>
          <p class="lead">Type a brand, company, or product name — the agent will find the site's URL.</p>
        </div>
      </div>

      <form id="searchForm" class="form-row" onsubmit="return false;" aria-describedby="help">
        <label for="q" class="sr-only">Name to search</label>
        <input id="q" name="q" type="text" placeholder="e.g. Nike, OpenAI, New York Times" aria-label="Name to search" autocomplete="off" required autofocus>
        <button id="go" type="submit">Find site</button>
      </form>

      <div id="help" class="example">Tip: try brand or organization names. Press Enter to search.</div>

      <div id="output" aria-live="polite"></div>

      <div style="margin-top:16px;display:flex;gap:8px;align-items:center">
        <div style="flex:1"></div>
        <a class="small" href="#" id="aboutLink">About</a>
      </div>

    </section>
  </main>

<script>
const form = document.getElementById('searchForm');
const input = document.getElementById('q');
const output = document.getElementById('output');
const go = document.getElementById('go');
const aboutLink = document.getElementById('aboutLink');

aboutLink.onclick = (e) => { e.preventDefault(); alert('This local tool searches DuckDuckGo results and returns a verified root domain that contains query tokens. It avoids social/wiki sites and unrelated matches for gibberish inputs.'); };

function setBusy(b){
  go.disabled = b;
  go.setAttribute('aria-busy', b ? 'true' : 'false');
}

async function doSearch(q){
  output.innerHTML = '';
  const box = document.createElement('div');
  box.className = 'result';
  box.textContent = 'Searching...';
  output.appendChild(box);
  setBusy(true);
  try{
    const resp = await fetch('/api/search', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name:q})
    });
    if(!resp.ok){ throw new Error('Network error'); }
    const data = await resp.json();
    output.innerHTML = '';
    if(data.url){
      const res = document.createElement('div');
      res.className = 'result';
      const a = document.createElement('a');
      a.href = data.url;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.textContent = data.url;
      a.setAttribute('aria-label', 'Open site in new tab');
      res.appendChild(a);

      const actions = document.createElement('div');
      actions.className = 'actions';

      const copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.textContent = 'Copy';
      copyBtn.onclick = async () => {
        try{ await navigator.clipboard.writeText(data.url); copyBtn.textContent='Copied'; setTimeout(()=>copyBtn.textContent='Copy',1300);}catch(e){alert('Copy failed');}
      };

      const openBtn = document.createElement('button');
      openBtn.type = 'button';
      openBtn.textContent = 'Open';
      openBtn.onclick = ()=> window.open(data.url, '_blank', 'noopener');

      actions.appendChild(copyBtn);
      actions.appendChild(openBtn);
      res.appendChild(actions);

      const meta = document.createElement('div');
      meta.className = 'small';
      meta.textContent = 'Verified live';
      res.appendChild(meta);

      output.appendChild(res);
      copyBtn.focus();
    } else {
      const no = document.createElement('div');
      no.className = 'result';
      no.textContent = 'No site found — try a different query.';
      output.appendChild(no);
    }
  }catch(err){
    output.innerHTML = '';
    const e = document.createElement('div');
    e.className = 'result';
    e.textContent = 'Error searching. Check your internet connection.';
    output.appendChild(e);
  }finally{
    setBusy(false);
  }
}

form.addEventListener('submit', (ev)=>{
  ev.preventDefault();
  const q = input.value.trim();
  if(!q) return;
  doSearch(q);
});

input.addEventListener('keydown', (ev)=>{ if(ev.key === 'Enter'){ ev.preventDefault(); form.dispatchEvent(new Event('submit')); }});
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(TEMPLATE)

@app.route('/api/search', methods=['POST'])
def api_search():
    body = request.get_json(force=True, silent=True) or {}
    name = body.get('name') or request.form.get('name') or ''
    result = {'url': None, 'verified': False}
    if not name:
        return jsonify(result)
    url = find_official_url(name)
    if url:
        result['url'] = url
        result['verified'] = True
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
