---
name: crawl4ai
description: Use the installed Crawl4AI 0.9.2 MCP server for rendered retrieval, clean Markdown or HTML, screenshots, PDFs, structured extraction, configurable crawling, JavaScript execution, and Crawl4AI documentation queries. Use whenever a task needs browser-rendered page content, visual/document capture, or extraction from modern websites.
---

# Crawl4AI MCP

Use the tools supplied by the named `crawl4ai` MCP server. Universal Agents
prefixes every upstream tool with `crawl4ai_` so its origin remains explicit.
Access is checked against the catalog tool `mcp:crawl4ai` and the original
upstream operation name, not the prefixed name. The agent process receives a
broker proxy and schemas, not the MCP endpoint credential.

There is no project-native crawl tool; the one Crawl4AI tool outside MCP is
`capture_web_screenshot` for exact-size viewport screenshots, which goes
through the broker as the web API tool `http:crawl4ai`. Do not use shell,
curl, Python HTTP clients, or a loopback URL to bypass the MCP server. The prefixed tools appear while the agent holds access to
`mcp:crawl4ai` for the person it works for. If they are absent, check
`list_mcp_connections` and `find_tools`, and report whether Crawl4AI is not
installed, not authorized for this person's work, or not loading: their
`load_status` says when the server is not answering (and when it is tried
again, or that administrators were told) or why the broker refused. Do not ask
for a restart; tools appear on the next step once installed and authorized.

For the shipped connection, inspect
`list_mcp_connections`. When the user requests setup and the connection is
pending, TeamArchitect calls `propose_access_change` with
`mcp_servers=[{"connection_id": ..., "record_digest": ...}]` from that listing
and a short reason. An administrator installs it on one Inbox card that also
lets TeamArchitect use all Crawl4AI tools and hand them on; the task waits,
then the tools appear. An administrator may also approve it directly in the
MCP controls. When it is installed but the tools are absent, call
`request_access` with `tool_id="mcp:crawl4ai"` and `level="full"`; full access
covers every Crawl4AI tool, so do not ask again for each one.

The shipped connection declares a credential slot (`credential_injections`):
the broker sends the Crawl4AI token as `Authorization: Bearer <token>` from the
stored credential linked to its catalog tool, `mcp:crawl4ai`, using the
person's own link first, then the team's while the team shares that tool
(the default; `/accounts` shows each tool's choice). The token is never an
environment variable (`CRAWL4AI_API_TOKEN` is refused at startup). When the
broker reports `account_link_missing` for `mcp:crawl4ai`, tell the person that
a team administrator links the team's token with `/link mcp:crawl4ai team` (and
`/link http:crawl4ai team` for `capture_web_screenshot`). `http:crawl4ai` is the
team's own server, so it takes only the team's token and is always shared. If
the team keeps `mcp:crawl4ai` private, its team token is not used and each
person links their own with `/link mcp:crawl4ai`. Or have
TeamArchitect load `secure-credential-workflows` and call `set_up_tools` for
`mcp:crawl4ai`, which opens the account link form without asking first. The person
picks a stored token in the broker's form, or types a new one there to save and
link it in one step. After a completed result, retry; the tools load on the
next step. Do not copy
the token, edit YAML, or create a duplicate connection.
Do not treat an OpenShell lease as MCP authority. Treat `active` as
installation state and `operator_configured` as the original configuration,
not proof of successful authentication. If the wrong account is linked, ask
the person to link the right one; the new link replaces the old one.

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

The server may add tools over time. A newly discovered or changed operation
needs `full` access until an operator confirms its level. Use an additional
`crawl4ai_*` tool only when it is actually attached and its live schema and
operator policy permit it.

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
operation. If the server refuses the operation, that is the operator's server
policy; do not bypass it through another tool or transport.

MCP bearer authentication is injected by the runtime. Never ask the user for
the Crawl4AI service token and never place it in tool input. Forward website
cookies or headers only when the task is authorized and the live MCP schema
provides a supported field or declarative hook for them.

## Failures

- Missing `crawl4ai_*` tools: inspect installed connection state when that tool
  is available. Tell the user whether the server is waiting for approval, the
  server is approved but this agent does not yet have access, the server's tool
  list has not been checked, the server is unavailable, or the current user
  cannot approve it. When the activation tool opens administrator review, direct
  the authorized administrator to **Settings > Inbox** and let approval resume
  setup. If review is unavailable, report the tool's reason and next step. Do
  not restart merely to refresh approved tools.
- `account_link_missing` or an authentication failure on a connection with
  credential slots: follow the account link steps above before asking for
  another credential or operator configuration changes. On a connection with
  operator-configured authentication, ask an administrator to check the
  server's token configuration.
- Other authentication or connection failure: report that the named Crawl4AI MCP
  server could not complete the requested action, state the reported reason,
  and suggest retrying or asking an administrator to check the server. Preserve
  the technical error details outside the plain-language summary.
- SSE POST failure or tool deadline: the runtime returns an error and reconnects
  before the next invocation, but it does not replay the failed request. Retry
  read-only retrieval or capture once. Do not retry JavaScript or another
  potentially mutating action unless the user confirms replay is safe.
- `access_denied` for `mcp:crawl4ai`: call `request_access` with the
  `tool_id` and `level` it names (normally `full` for the whole server) and a
  plain reason. Retry only
  when the result says `granted`; after a denial, do not retry or use another
  tool to get around it.
- Rejected configuration: remove or correct the rejected field according to
  the live schema or consult `crawl4ai_ask`.
- JavaScript or hook denial: respect the server policy and use a lower-risk
  supported operation where it can still satisfy the request.
- Target-site block or timeout: retry only with bounded, relevant browser
  settings, then use another authorized source if appropriate.

Do not interpret an MCP routing or authorization failure as evidence that the
target website itself cannot be rendered.
