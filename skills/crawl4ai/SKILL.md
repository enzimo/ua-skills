---
name: crawl4ai
description: Use the attached Crawl4AI 0.9.1 MCP server for rendered retrieval, clean Markdown or HTML, screenshots, PDFs, structured extraction, configurable crawling, JavaScript execution, and Crawl4AI documentation queries. Use whenever a task needs browser-rendered page content, visual/document capture, or extraction from modern websites.
---

# Crawl4AI MCP

Use the tools supplied by the named `crawl4ai` MCP server. Universal Agents
prefixes every upstream tool with `crawl4ai_` so its origin remains explicit
and can become a Cedar authorization resource.

Do not call the dormant project-native `crawl4ai(operation=...)` implementation.
Do not use shell, curl, Python HTTP clients, or a loopback URL to bypass the MCP
server. If the prefixed tools are absent, report that Crawl4AI MCP access is not
attached or authorized for the current agent.

## Available Tools

Use the model-visible MCP schema as the authority for each call. Crawl4AI 0.9.1
normally exposes:

| Tool | Use |
|---|---|
| `crawl4ai_md` | Render one page and return Markdown with supported filtering options |
| `crawl4ai_html` | Return preprocessed HTML for inspection or schema design |
| `crawl4ai_screenshot` | Capture a rendered full-page PNG |
| `crawl4ai_pdf` | Render a page as PDF |
| `crawl4ai_execute_js` | Execute explicit browser JavaScript when the service permits it |
| `crawl4ai_crawl` | Crawl one or more URLs with the full MCP-exposed browser, crawler, extraction, hook, and streaming configuration |
| `crawl4ai_ask` | Query Crawl4AI's indexed documentation and library context |

The server may add tools over time. Use any additional `crawl4ai_*` tool when
its live schema matches the task and operator policy permits it.

## Workflow

1. Choose the narrowest upstream tool that produces the requested result.
2. Read its live schema before composing advanced arguments. Use
   `crawl4ai_ask` when a configuration or result field is unclear.
3. Prefer `crawl4ai_md` for readable source material and `crawl4ai_crawl` for
   multiple URLs, extraction strategies, browser settings, crawler settings,
   declarative hooks, or streaming behavior.
4. Use `crawl4ai_html` when Markdown removes structure needed to design a CSS,
   XPath, regex, or other supported extraction strategy.
5. Use `crawl4ai_screenshot` or `crawl4ai_pdf` whenever the user requests a
   visual or document capture. Preserve and deliver the MCP result content in
   the response path supported by the active agent runtime.
6. Keep URL batches bounded and use focused extraction/filtering so large page
   bodies do not overwhelm the model context.

## Extraction and Browser Configuration

Pass `BrowserConfig`, `CrawlerRunConfig`, Markdown generators, content filters,
and extraction strategies only through fields present in the live
`crawl4ai_crawl` schema. Prefer deterministic CSS, XPath, LXML, or regex
extraction when the page structure supports it; use server-backed LLM
extraction only when deterministic strategies are unsuitable.

Crawl4AI 0.9.1 accepts declarative hook actions rather than arbitrary Python
hook code. Use only hook actions accepted by the live schema. Never attempt to
smuggle code, credentials, provider keys, proxy settings, persistent sessions,
or unsupported browser initialization through unrelated fields.

## JavaScript and Credentials

Treat `crawl4ai_execute_js` as high risk. Use it only when JavaScript is
necessary for the requested page interaction and the server has enabled the
operation. A denied call is an operator-policy boundary; do not bypass it
through another tool or transport.

MCP bearer authentication is injected by the runtime. Never ask the user for
the Crawl4AI service token and never place it in tool input. Forward website
cookies or headers only when the task is authorized and the live MCP schema
provides a supported field or declarative hook for them.

## Failures

- Missing `crawl4ai_*` tools: the current agent lacks the configured or
  authorized MCP server; report that boundary.
- Authentication or connection failure: report that the named Crawl4AI MCP
  server is unavailable and preserve the error details.
- Rejected configuration: remove or correct the rejected field according to
  the live schema or consult `crawl4ai_ask`.
- JavaScript or hook denial: respect the server policy and use a lower-risk
  supported operation where it can still satisfy the request.
- Target-site block or timeout: retry only with bounded, relevant browser
  settings, then use another authorized source if appropriate.

Do not interpret an MCP routing or authorization failure as evidence that the
target website itself cannot be rendered.
