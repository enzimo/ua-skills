---
name: searxng-search
description: Privacy-respecting metasearch via a configurable SearXNG instance. Use for web search, news, images, videos, and specialized queries without tracking.
---

# SearXNG Search Skill

This skill queries the SearXNG instance configured with `SEARXNG_BASE_URL`.
Examples default to `http://127.0.0.1:8080` and perform privacy-respecting
metasearch across many engines with a single request.

## When to Use

- General web search without tracking
- News, images, videos, maps, music, science papers, IT/code search
- Aggregating results across multiple engines
- When you need JSON-formatted search results programmatically

## Endpoint

- Base URL: `${SEARXNG_BASE_URL:-http://127.0.0.1:8080}`
- Search path: `/search`
- Method: `GET` (also accepts `POST`)

## Credential Handling

Use the configured public instance without credentials. If a different SearXNG
deployment requires an API key, proxy token, or HTTP auth, use credentials
already hydrated in the environment, CLI, credential store, or secret-file
mounts. Do not ask the user to paste credentials into chat; instruct them to
provide missing credentials through the runtime credential collection form.

## Core Parameters

| Param        | Required | Description                                                       |
|--------------|----------|-------------------------------------------------------------------|
| `q`          | yes      | Query string. Supports `!bang` syntax for engine/category routing |
| `format`     | no       | `json`, `csv`, `rss` (default: HTML). Use `json` for scripting    |
| `categories` | no       | Comma list: `general,news,images,videos,it,science,map,music`     |
| `engines`    | no       | Comma list of specific engines (e.g. `google,duckduckgo`)         |
| `language`   | no       | Locale code, e.g. `en-US`, `all`                                  |
| `pageno`     | no       | Page number (1-indexed)                                           |
| `time_range` | no       | `day`, `week`, `month`, `year`                                    |
| `safesearch` | no       | `0` off, `1` moderate, `2` strict                                 |

> Note: Public instances often disable `format=json`. If JSON is blocked,
> fall back to scraping HTML or use the RSS format.

## Bang Syntax (in `q`)

- `!go climate change` → Google only
- `!images cats` → image category
- `!news ukraine` → news category
- `!wp linux` → Wikipedia

## Examples

When running an example through Universal Agents, load
`shell-execution-workflows`, pass the underlying command without an `rtk`
prefix, and set an explicit timeout. Inspect status, exit code, separate
output/error, termination reason, RTK mode, and warnings. The shell blocks
localhost and loopback targets; configure a reachable endpoint or use a
broker-owned request tool for a local/private SearXNG deployment.

### 1. Simple JSON search (curl)

```bash
SEARXNG_BASE_URL="${SEARXNG_BASE_URL:-http://127.0.0.1:8080}"
curl -G "$SEARXNG_BASE_URL/search" \
  --data-urlencode 'q=open source LLMs' \
  --data-urlencode 'format=json' \
  --data-urlencode 'language=en-US'
```

### 2. Python client

```python
import os

import requests
from urllib.parse import urlencode

BASE = os.getenv("SEARXNG_BASE_URL", "http://127.0.0.1:8080")

def searxng_search(
    query: str,
    categories: str = "general",
    language: str = "en-US",
    pageno: int = 1,
    time_range: str | None = None,
    safesearch: int = 1,
    fmt: str = "json",
):
    params = {
        "q": query,
        "categories": categories,
        "language": language,
        "pageno": pageno,
        "safesearch": safesearch,
        "format": fmt,
    }
    if time_range:
        params["time_range"] = time_range

    r = requests.get(
        f"{BASE}/search",
        params=params,
        headers={"User-Agent": "Mozilla/5.0 (skill/searxng)"},
        timeout=20,
    )
    r.raise_for_status()
    if fmt == "json":
        return r.json()
    return r.text


if __name__ == "__main__":
    data = searxng_search("rust async runtimes 2026", time_range="month")
    for hit in data.get("results", [])[:10]:
        print(f"- {hit['title']}\n  {hit['url']}\n")
```

### 3. Node.js client

```js
const BASE = process.env.SEARXNG_BASE_URL ?? "http://127.0.0.1:8080";

export async function searxngSearch(query, opts = {}) {
  const params = new URLSearchParams({
    q: query,
    format: "json",
    language: opts.language ?? "en-US",
    categories: opts.categories ?? "general",
    pageno: String(opts.pageno ?? 1),
    safesearch: String(opts.safesearch ?? 1),
    ...(opts.timeRange ? { time_range: opts.timeRange } : {}),
  });

  const res = await fetch(`${BASE}/search?${params}`, {
    headers: { "User-Agent": "skill/searxng" },
  });
  if (!res.ok) throw new Error(`SearXNG ${res.status}`);
  return res.json();
}
```

### 4. HTML fallback (when JSON disabled)

```python
import os

from bs4 import BeautifulSoup
import requests

def searxng_html(q):
    base = os.getenv("SEARXNG_BASE_URL", "http://127.0.0.1:8080")
    r = requests.get(
        f"{base}/search",
        params={"q": q},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    soup = BeautifulSoup(r.text, "html.parser")
    return [
        {
            "title": a.get_text(strip=True),
            "url": a["href"],
            "snippet": (a.find_parent("article").select_one("p")
                        or {}).get_text(strip=True) if a.find_parent("article") else "",
        }
        for a in soup.select("article h3 a")
    ]
```

## Response Shape (JSON)

```json
{
  "query": "open source LLMs",
  "number_of_results": 0,
  "results": [
    {
      "url": "https://example.com/...",
      "title": "...",
      "content": "snippet text",
      "engine": "google",
      "score": 1.23,
      "category": "general",
      "publishedDate": "2026-04-01T00:00:00"
    }
  ],
  "answers": [],
  "infoboxes": [],
  "suggestions": ["..."],
  "unresponsive_engines": []
}
```

## Best Practices

1. **Rate limit yourself.** Public instances may rate-limit; cap to ~1 req/sec
   and cache results locally.
2. **Set a User-Agent.** Some instances block empty UAs.
3. **Handle JSON-disabled instances.** Detect HTML response and either parse
   it or surface a clear error.
4. **Respect the operator.** Don't scrape aggressively; this is a free
   community instance.
5. **Combine `engines` + `categories`** for targeted queries (e.g. only
   `engines=arxiv,pubmed` for research).
6. **Use `time_range`** for fresh news; otherwise stale results dominate.
7. **Fallback strategy:** if a query returns empty `results`, retry with
   different `engines` or remove `time_range`.

## Common Recipes

- **News last 24h:** `categories=news&time_range=day`
- **Academic papers:** `categories=science&engines=arxiv,semantic_scholar,pubmed`
- **Code/IT:** `categories=it&engines=github,stackoverflow`
- **Images only:** `categories=images&safesearch=2`

## Error Handling

| Status | Meaning                       | Action                              |
|--------|-------------------------------|-------------------------------------|
| 429    | Rate limited                  | Backoff, retry with jitter          |
| 403    | Format/UA blocked             | Switch to HTML or set proper UA     |
| 5xx    | Upstream engine failures      | Retry once; check `unresponsive_engines` |
