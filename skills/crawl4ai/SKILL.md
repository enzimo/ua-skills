---
name: crawl4ai
description: Use the attached Crawl4AI 0.9.2 MCP server for rendered retrieval, clean Markdown or HTML, screenshots, PDFs, structured extraction, configurable crawling, JavaScript execution, and Crawl4AI documentation queries. Use whenever a task needs browser-rendered page content, visual/document capture, or extraction from modern websites.
---

# Crawl4AI MCP

Use the tools supplied by the named `crawl4ai` MCP server. Universal Agents
prefixes every upstream tool with `crawl4ai_` so its origin remains explicit
while the original upstream operation remains the exact Cedar authorization
resource. The agent process receives a broker proxy and schemas, not the MCP
endpoint credential.

Do not call the dormant project-native `crawl4ai(operation=...)` implementation.
Do not use shell, curl, Python HTTP clients, or a loopback URL to bypass the MCP
server. If the prefixed tools are absent, report that Crawl4AI MCP access is not
installed, discovered, attached, available, or authorized for the current
agent. Installation, initial discovery, and attachment to an agent type are
separate authorities. Do not ask for a restart; approved, discovered, and
attached MCP connections become available at a safe turn boundary.

The shipped Crawl4AI connection uses operator-configured authentication. After
the connection itself is approved, submit the exact
`mcp.connection.discover` denial receipt for authenticated same-team
administrator review. Wait for the persisted decision, retry activation, and
then request the separate owner-reviewed attachment. An empty permission view
for a non-administrator does not mean the discovery request disappeared.

## Available Tools

Use the model-visible MCP schema as the authority for each call. Crawl4AI 0.9.2
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

The server may add tools over time, but newly discovered operations or schema
changes remain quarantined until their exact catalog update is reviewed. Use an
additional `crawl4ai_*` tool only when it is actually attached and its live
schema and operator policy permit it.

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

Crawl4AI 0.9.2 accepts declarative hook actions rather than arbitrary Python
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

- Missing `crawl4ai_*` tools: inspect installed connection state when that tool
  is available. Tell the user whether the server is waiting for approval, the
  server is approved but this agent does not yet have access, the server's tool
  list has not been checked, the server is unavailable, or the current user
  cannot approve it. If an administrator must approve the tool-list check, tell
  the user to open **Settings > Needs Approval**. After approval, retry the
  connection and request the separate agent access. Do not restart to refresh
  it.
- Authentication or connection failure: report that the named Crawl4AI MCP
  server could not complete the requested action, state the reported reason,
  and suggest retrying or asking an administrator to check the server. Preserve
  the technical error details outside the plain-language summary.
- SSE POST failure or tool deadline: the runtime returns an error and reconnects
  before the next invocation, but it does not replay the failed request. Retry
  read-only retrieval or capture once. Do not retry JavaScript or another
  potentially mutating action unless the user confirms replay is safe.
- Rejected configuration: remove or correct the rejected field according to
  the live schema or consult `crawl4ai_ask`.
- JavaScript or hook denial: respect the server policy and use a lower-risk
  supported operation where it can still satisfy the request.
- Target-site block or timeout: retry only with bounded, relevant browser
  settings, then use another authorized source if appropriate.

Do not interpret an MCP routing or authorization failure as evidence that the
target website itself cannot be rendered.
