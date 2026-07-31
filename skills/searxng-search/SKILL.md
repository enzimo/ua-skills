---
name: searxng-search
description: Use the brokered SearXNG metasearch service for current web, news, image, video, map, music, science, file, social, and specialized engine searches; capability discovery; suggestions; bang syntax; pagination; SafeSearch; time filters; and JSON, CSV, or RSS artifacts. Do not access a local SearXNG instance with shell or curl.
---

# SearXNG Search

Use the single `searxng(operation=...)` tool. It owns private routing,
timeouts, output parsing, and workspace artifacts. Never use shell, curl, a
Python HTTP client, or loopback routing to reach the configured instance.

## Operations

- `capabilities`: discover the live version, categories, engines, shortcuts,
  locales, plugins, paging/SafeSearch/time-range support, and engine errors.
- `search`: run metasearch and preserve both normalized results and the raw
  response artifact.
- `suggest`: request autocomplete suggestions.

Call `capabilities` before selecting unfamiliar engine names or specialized
categories. Live instance configuration is authoritative.

## Search

```text
searxng(
  operation="search",
  query="open source agent frameworks",
  categories="general,it",
  language="en-US",
  page=1,
  safesearch=1,
  output_format="json",
  max_results=10
)
```

Useful parameters:

| Parameter | Meaning |
|---|---|
| `query` | Search text, including SearXNG engine/category/language syntax |
| `categories` | Comma-separated live categories such as `general,news,images,videos,it,science,map,music,files,social media` |
| `engines` | Comma-separated live engine names or shortcuts |
| `language` | Locale such as `en-US`, `fr`, or `all` |
| `page` | One-indexed result page |
| `time_range` | Empty, `day`, `month`, or `year` |
| `safesearch` | `0` off, `1` moderate, `2` strict |
| `output_format` | `json`, `csv`, or `rss` |
| `max_results` | Bounded count normalized inline; full service output remains in `raw_file` |

The `options` mapping exposes supported search preferences without adding more
tools: `enabled_engines`, `disabled_engines`, `enabled_plugins`,
`disabled_plugins`, `image_proxy`, `results_on_new_tab`, and `theme`.

## Search Syntax and Recipes

SearXNG accepts modifiers inside `query`:

- `!wp paris`: Wikipedia engine.
- `!images Wau Holland`: image category.
- `!map coffee Austin`: map category.
- `:fr !news élections`: French-language news.
- Multiple modifiers are inclusive, such as `!ddg !wp query`.

Common calls:

```text
searxng(operation="search", query="AI regulation", categories="news", time_range="day")
searxng(operation="search", query="vector database benchmark", categories="science,it", engines="arxiv,github")
searxng(operation="search", query="red panda", categories="images", safesearch=2)
searxng(operation="suggest", query="crawl4ai")
```

Engine availability varies. If a targeted query is empty, remove `engines` or
`time_range`, inspect `unresponsive_engines`, and retry once with broader live
capabilities.

## Results and Artifacts

JSON searches return compact normalized results containing title, URL, snippet,
engine, score, category, result type, publication date, and a `details` mapping.
`details` preserves type-specific fields for images, videos, maps, torrents,
packages, scientific papers, and other engine templates. The result also keeps
answers, corrections, suggestions, infoboxes, and unresponsive-engine reports.

Use `raw_file` when the normalized view omits a provider-specific field, and
read it with `web_artifact_inspect` rather than loading the whole file. CSV and
RSS searches return a saved path plus a bounded preview.

External-bang redirects are intentionally not followed. A redirect result
includes the destination and a privacy warning so the caller can decide whether
leaving SearXNG is appropriate.

## Failure Handling

- 403 normally means the requested output format is not enabled. The bundled
  deployment enables JSON, CSV, and RSS; for another instance, ask its operator
  to add the format under `search.formats`.
- 429 means rate limiting; back off and narrow or defer the request.
- A successful response can still list failing upstream engines. Treat
  `unresponsive_engines` as a coverage caveat, not a total search failure.
- On connection or timeout failures, use the returned `retryable` flag and
  mitigation hints. Do not bypass the broker with direct local HTTP.

For time-sensitive or contested research, compare SearXNG with another
independent provider when tool budget allows, and report coverage differences.
