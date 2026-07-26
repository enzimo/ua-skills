---
name: crawl4ai
description: LLM-friendly web crawling/scraping via a configurable Crawl4AI service. Produces clean Markdown, supports JS rendering, structured extraction, and aggressive content filtering to keep context windows lean.
---

# Crawl4AI Service Skill

Crawl4AI is exposed as an HTTP service configured with `CRAWL4AI_BASE`.
The examples default to `http://127.0.0.1:11235`. You send JSON and get clean
Markdown (or structured JSON) back—no Playwright, Python dependencies, or
browser management required.

## When to Use

- Fetching JS-rendered pages (SPAs)
- Producing LLM-ready Markdown for RAG / Q&A
- Bulk scraping a list of URLs
- Structured extraction (CSS/XPath schemas, or LLM-driven)
- Anytime you'd reach for `requests` + `beautifulsoup` — use this instead

## Base URL & Health

- Base: `${CRAWL4AI_BASE:-http://127.0.0.1:11235}`
- Health: `GET /health`
- Schema/Playground: `GET /schema`, `GET /playground` (interactive docs)
- OpenAPI: `GET /openapi.json`

```bash
CRAWL4AI_BASE="${CRAWL4AI_BASE:-http://127.0.0.1:11235}"
curl "$CRAWL4AI_BASE/health"
```

## Universal Agents Shell Behavior

Before running these `curl` examples through Universal Agents, load
`shell-execution-workflows`. Pass the underlying command without an `rtk`
prefix, add an explicit shell timeout, and inspect status, exit code, separate
output/error, termination reason, RTK mode, and warnings. Use sequential command
lists for dependent requests and `parallel=true` only for independent URLs.
Universal Agents closes stdin and provides no PTY, so keep every request fully
non-interactive.

## Credential Handling

Most Crawl4AI calls need no agent-held credential. For LLM-backed filters or
extraction, prefer provider tokens already hydrated in the service, CLI
environment, credential store, or secret-file mounts, using references such as
`env:OPENAI_API_KEY`.

Do not ask the user to paste API keys into chat or examples. If a required LLM
provider key is missing, instruct the user to provide it through the runtime
credential collection form, then retry with an environment or secret-file
reference. When credential collection is not available, use non-LLM filters such
as `PruningContentFilter` or `BM25ContentFilter`.

## Core Endpoints

| Endpoint           | Method | Purpose                                              |
|--------------------|--------|------------------------------------------------------|
| `/md`              | POST   | Quick: URL → Markdown (with optional filter)         |
| `/html`            | POST   | Preprocessed/sanitized HTML                          |
| `/screenshot`      | POST   | Full-page PNG (base64)                               |
| `/pdf`             | POST   | Full-page PDF (base64)                               |
| `/crawl`           | POST   | Full power: one or many URLs, all configs           |
| `/crawl/stream`    | POST   | NDJSON stream of results (good for many URLs)       |
| `/execute_js`      | POST   | Run JS snippets on a page, get result               |
| `/ask` / `/llm`    | POST   | Crawl + ask an LLM about the content (if enabled)   |

## 1. Quickest Path — `/md`

Use this when you just want clean Markdown.

```bash
CRAWL4AI_BASE="${CRAWL4AI_BASE:-http://127.0.0.1:11235}"
curl -X POST "$CRAWL4AI_BASE/md" \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://example.com",
    "f": "fit",
    "q": null,
    "c": "0"
  }'
```

Parameters:

| Field | Type   | Description                                                  |
|-------|--------|--------------------------------------------------------------|
| `url` | string | Target URL                                                   |
| `f`   | string | Filter: `raw`, `fit` (pruning), `bm25`, `llm`               |
| `q`   | string | Query — required for `bm25` / `llm` filters                  |
| `c`   | string | Cache-busting token (`"0"` = use cache, anything else fresh) |

Response:

```json
{
  "url": "https://example.com",
  "filter": "fit",
  "query": null,
  "cache": "0",
  "markdown": "# Example Domain\n..."
}
```

> **Token tip:** Always prefer `f=fit` over `f=raw`. Use `f=bm25` with a
> `q` when you know what you're looking for — it can cut tokens 5–10×.

## 2. Full Power — `/crawl`

Accepts one or more URLs plus `BrowserConfig` and `CrawlerRunConfig`.

```bash
CRAWL4AI_BASE="${CRAWL4AI_BASE:-http://127.0.0.1:11235}"
curl -X POST "$CRAWL4AI_BASE/crawl" \
  -H 'Content-Type: application/json' \
  -d '{
    "urls": ["https://news.ycombinator.com"],
    "browser_config": {
      "type": "BrowserConfig",
      "params": {
        "headless": true,
        "user_agent_mode": "random",
        "viewport_width": 1280,
        "viewport_height": 800
      }
    },
    "crawler_config": {
      "type": "CrawlerRunConfig",
      "params": {
        "cache_mode": "BYPASS",
        "word_count_threshold": 15,
        "excluded_tags": ["nav", "footer", "header", "aside", "form"],
        "exclude_external_links": true,
        "exclude_social_media_links": true,
        "remove_overlay_elements": true,
        "wait_until": "domcontentloaded",
        "page_timeout": 30000,
        "markdown_generator": {
          "type": "DefaultMarkdownGenerator",
          "params": {
            "options": {"ignore_images": true, "body_width": 0},
            "content_filter": {
              "type": "PruningContentFilter",
              "params": {
                "threshold": 0.48,
                "threshold_type": "dynamic",
                "min_word_threshold": 10
              }
            }
          }
        }
      }
    }
  }'
```

Response shape:

```json
{
  "success": true,
  "results": [
    {
      "url": "...",
      "success": true,
      "status_code": 200,
      "html": "...",
      "cleaned_html": "...",
      "markdown": {
        "raw_markdown": "...",
        "fit_markdown": "...",
        "markdown_with_citations": "...",
        "references_markdown": "..."
      },
      "extracted_content": null,
      "links": {"internal": [], "external": []},
      "media": {"images": [], "videos": [], "audios": []},
      "metadata": {"title": "...", "description": "..."}
    }
  ]
}
```

**Always read `results[i].markdown.fit_markdown` for LLM context.**

## 3. Streaming Bulk — `/crawl/stream`

Same body as `/crawl`, but the response is NDJSON (one JSON object per
line) so you can start processing before the whole batch finishes.

```bash
CRAWL4AI_BASE="${CRAWL4AI_BASE:-http://127.0.0.1:11235}"
curl -N -X POST "$CRAWL4AI_BASE/crawl/stream" \
  -H 'Content-Type: application/json' \
  -d '{"urls": ["https://a.com","https://b.com","https://c.com"],
       "crawler_config":{"type":"CrawlerRunConfig","params":{"cache_mode":"ENABLED"}}}'
```

## Config Object Format

The service uses a tagged-union convention everywhere:

```json
{ "type": "<ClassName>", "params": { ... } }
```

This applies to `BrowserConfig`, `CrawlerRunConfig`,
`DefaultMarkdownGenerator`, all content filters, all extraction
strategies, and all deep-crawl strategies.

## Content Filtering — The Token-Saver

Pick one filter and embed it under
`crawler_config.params.markdown_generator.params.content_filter`.

### `PruningContentFilter` — heuristic, fast, no LLM cost

```json
{
  "type": "PruningContentFilter",
  "params": {
    "threshold": 0.5,
    "threshold_type": "dynamic",
    "min_word_threshold": 20
  }
}
```

### `BM25ContentFilter` — query-aware, brutal token reduction

```json
{
  "type": "BM25ContentFilter",
  "params": {
    "user_query": "pricing tiers and enterprise plan limits",
    "bm25_threshold": 1.2
  }
}
```

### `LLMContentFilter` — highest fidelity, costs LLM tokens

```json
{
  "type": "LLMContentFilter",
  "params": {
    "llm_config": {
      "type": "LLMConfig",
      "params": {"provider": "openai/gpt-4o-mini", "api_token": "env:OPENAI_API_KEY"}
    },
    "instruction": "Keep only API reference content. Drop marketing copy.",
    "chunk_token_threshold": 4096
  }
}
```

## Structured Extraction (no LLM needed)

For predictable layouts — zero LLM cost, deterministic JSON output.

```json
"extraction_strategy": {
  "type": "JsonCssExtractionStrategy",
  "params": {
    "schema": {
      "name": "HN Stories",
      "baseSelector": "tr.athing",
      "fields": [
        {"name": "title", "selector": "span.titleline > a", "type": "text"},
        {"name": "url",   "selector": "span.titleline > a", "type": "attribute", "attribute": "href"}
      ]
    }
  }
}
```

Result lands in `results[i].extracted_content` as a JSON string.

For unstructured pages, use `LLMExtractionStrategy` with a JSON schema
and an `instruction`.

## JS Interaction (SPAs, infinite scroll)

```json
"crawler_config": {
  "type": "CrawlerRunConfig",
  "params": {
    "js_code": [
      "window.scrollTo(0, document.body.scrollHeight);",
      "document.querySelectorAll('button.load-more').forEach(b=>b.click());"
    ],
    "wait_for": "css:.results-loaded",
    "wait_until": "networkidle",
    "page_timeout": 60000,
    "session_id": "my-session",
    "js_only": false
  }
}
```

Reuse `session_id` across calls to keep the same page open and click
through multi-step flows. Set `js_only: true` on follow-ups to avoid
reloading.

## Deep Crawling

```json
"crawler_config": {
  "type": "CrawlerRunConfig",
  "params": {
    "stream": true,
    "deep_crawl_strategy": {
      "type": "BFSDeepCrawlStrategy",
      "params": {
        "max_depth": 2,
        "max_pages": 50,
        "include_external": false,
        "filter_chain": {
          "type": "FilterChain",
          "params": {
            "filters": [
              {"type":"DomainFilter","params":{"allowed_domains":["docs.example.com"]}},
              {"type":"URLPatternFilter","params":{"patterns":["*/api/*","*/guide/*"]}},
              {"type":"ContentTypeFilter","params":{"allowed_types":["text/html"]}}
            ]
          }
        }
      }
    }
  }
}
```

Pair with `/crawl/stream` so results arrive incrementally.

## Python Client (using the service)

```python
import os

import requests

BASE = os.getenv("CRAWL4AI_BASE", "http://127.0.0.1:11235")

def md(url: str, query: str | None = None, fresh: bool = False) -> str:
    body = {
        "url": url,
        "f": "bm25" if query else "fit",
        "q": query,
        "c": "1" if fresh else "0",
    }
    r = requests.post(f"{BASE}/md", json=body, timeout=60)
    r.raise_for_status()
    return r.json()["markdown"]

def crawl(urls, *, query=None, css_schema=None, deep=False):
    cfg = {
        "cache_mode": "BYPASS",
        "word_count_threshold": 15,
        "excluded_tags": ["nav","footer","header","aside","form"],
        "exclude_external_links": True,
        "remove_overlay_elements": True,
        "wait_until": "domcontentloaded",
        "page_timeout": 30000,
        "markdown_generator": {
            "type": "DefaultMarkdownGenerator",
            "params": {
                "options": {"ignore_images": True, "body_width": 0},
                "content_filter": (
                    {"type":"BM25ContentFilter","params":{"user_query":query,"bm25_threshold":1.2}}
                    if query else
                    {"type":"PruningContentFilter","params":{"threshold":0.48,"threshold_type":"dynamic","min_word_threshold":10}}
                ),
            },
        },
    }
    if css_schema:
        cfg["extraction_strategy"] = {
            "type": "JsonCssExtractionStrategy",
            "params": {"schema": css_schema},
        }

    body = {
        "urls": urls if isinstance(urls, list) else [urls],
        "browser_config": {"type":"BrowserConfig","params":{"headless":True,"user_agent_mode":"random"}},
        "crawler_config": {"type":"CrawlerRunConfig","params": cfg},
    }
    r = requests.post(f"{BASE}/crawl", json=body, timeout=120)
    r.raise_for_status()
    return r.json()["results"]


# Example
print(md("https://example.com"))
print(md("https://stripe.com/pricing", query="enterprise plan limits"))
```

## Node.js Client

```js
const BASE = process.env.CRAWL4AI_BASE ?? "http://127.0.0.1:11235";

export async function md(url, { query = null, fresh = false } = {}) {
  const body = { url, f: query ? "bm25" : "fit", q: query, c: fresh ? "1" : "0" };
  const r = await fetch(`${BASE}/md`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`crawl4ai ${r.status}`);
  return (await r.json()).markdown;
}

export async function crawl(urls, runParams = {}) {
  const r = await fetch(`${BASE}/crawl`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      urls: Array.isArray(urls) ? urls : [urls],
      browser_config: { type: "BrowserConfig", params: { headless: true } },
      crawler_config: { type: "CrawlerRunConfig", params: runParams },
    }),
  });
  if (!r.ok) throw new Error(`crawl4ai ${r.status}`);
  return (await r.json()).results;
}
```

## Token-Budget Playbook

When the goal is "fit this page in N tokens", apply in order:

1. **Use `/md` with `f=fit`** for one-off pages. Simplest win.
2. **Switch to `f=bm25` with a `q`** if you have a question — biggest cut.
3. **In `/crawl`, set `excluded_tags`** to nuke nav/footer/aside.
4. **`exclude_external_links: true`** — link soup eats tokens fast.
5. **`remove_overlay_elements: true`** — kills cookie/newsletter modals.
6. **`word_count_threshold: 15–25`** drops short cruft blocks.
7. **`PruningContentFilter` threshold `0.48–0.6`** — dial up if needed.
8. **`ignore_images: true`** in markdown options.
9. **Always read `markdown.fit_markdown`**, never `raw_markdown`.
10. **Use `JsonCssExtractionStrategy`** when you only need 5 fields —
    don't ship the whole article.
11. **Pre-filter URLs** in deep crawls (`DomainFilter`, `URLPatternFilter`)
    so junk pages never get fetched.

Typical result: news article ~8k tokens raw → ~1.2k `fit_markdown` →
~300 tokens with BM25 + a focused query. No meaningful info loss.

## Caching

Set `crawler_config.params.cache_mode` to one of:
`ENABLED`, `BYPASS`, `DISABLED`, `READ_ONLY`, `WRITE_ONLY`.
For `/md`, use `c: "0"` for cached, any other value busts cache.

## Anti-Bot Settings

```json
"browser_config": {
  "type": "BrowserConfig",
  "params": {
    "headless": true,
    "user_agent_mode": "random",
    "extra_args": ["--disable-blink-features=AutomationControlled"]
  }
},
"crawler_config": {
  "type": "CrawlerRunConfig",
  "params": {
    "magic": true,
    "simulate_user": true,
    "override_navigator": true
  }
}
```

## Inspecting a Result

```text
results[i].success                       bool
results[i].status_code                   HTTP status
results[i].markdown.fit_markdown         ← USE THIS for LLMs
results[i].markdown.raw_markdown         full conversion
results[i].markdown.markdown_with_citations + .references_markdown
results[i].cleaned_html                  filtered HTML
results[i].extracted_content             JSON string (if extraction used)
results[i].links.internal / .external
results[i].media.images / .videos / .audios
results[i].metadata.title / .description / og tags
```

## Common Pitfalls

- **Reading `raw_markdown` by accident** — always `fit_markdown` for LLMs.
- **Forgetting the `{type, params}` wrapper** — every config object needs it.
- **`wait_until: "load"` on SPAs** — use `"domcontentloaded"` plus
  `wait_for: "css:..."`, or `"networkidle"`.
- **Pruning threshold too aggressive** — start at `0.45`, raise carefully.
- **Unbounded deep crawls** — always set `max_pages` and `max_depth`.
- **Reusing `session_id` across unrelated jobs** — sessions hold cookies.
- **Hammering the service** — cache when you can; be a good neighbor.

## Quick Recipe Index

| Goal                              | Endpoint + Combo                                       |
|-----------------------------------|--------------------------------------------------------|
| One page → clean MD               | `POST /md` with `f=fit`                                |
| Targeted Q&A from one page        | `POST /md` with `f=bm25` + `q="..."`                  |
| Scrape product list               | `/crawl` + `JsonCssExtractionStrategy`                 |
| Crawl docs site                   | `/crawl/stream` + `BFSDeepCrawlStrategy` + `DomainFilter` |
| Infinite scroll                   | `/crawl` + `js_code` + `session_id` + follow-ups with `js_only: true` |
| Screenshot                        | `POST /screenshot`                                     |
| PDF snapshot                      | `POST /pdf`                                            |
| Run JS, get value                 | `POST /execute_js`                                     |
| Maximum cleanup                   | Pruning + `excluded_tags` + `ignore_images` + `word_count_threshold: 20` |
