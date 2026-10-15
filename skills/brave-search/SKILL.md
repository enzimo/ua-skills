---
name: brave-search
description: Use Brave Search API for independent-index web search, LLM grounding context, freshness filters, Goggles ranking, and search-provider preference or comparison workflows.
---

# Brave Search Skill

Use this skill when a task involves Brave Search API, search-provider choice,
provider preference, or comparing results across search tools.

## Search Preference Policy

Follow explicit provider instructions first:

- If the user or manager says "prefer Brave", start with Brave.
- If they say "prefer Exa", start with Exa.
- If they ask to compare providers, run the requested providers and report
  agreement, disagreement, coverage gaps, and source-quality differences.
- If no provider is specified, choose the smallest search workflow that fits
  the task.

Default hierarchy:

- Brave: broad and current web discovery from Brave's independent index,
  freshness filters, news-like recency, Goggles, and source diversity checks.
- Brave LLM Context: when the agent needs pre-extracted grounding content in
  one call rather than only ranked links and snippets.
- Exa: semantic/neural search, content-enriched search, or when Exa's result
  model is a better match for concepts, papers, companies, and technical pages.
- `searxng(operation="search")`: alternate engine coverage, metasearch
  comparison, and auditable search-result artifacts.
- `crawl4ai_md` or `crawl4ai_crawl`: rendered retrieval through the Crawl4AI
  MCP server and source inspection after search has identified likely pages.

Compare at least two complementary search sources when tool budget allows and
the answer is high-stakes, fast-changing, commercial, contested, or likely to be
distorted by SEO/review bias.

## Universal Agents Tools

When these tools are available, prefer them over shell/curl because they save
full responses under the task's web-research artifact tree and return compact
model-safe summaries:

- `brave_web_search_artifact`: ranked Brave web results with snippets, URLs,
  freshness filters, SafeSearch, result filters, and optional Goggles.
- `brave_llm_context_artifact`: Brave's pre-extracted grounding context for
  agent/RAG use, with bounded preview text plus saved raw artifacts.

Use the prefixed Crawl4AI MCP tools on selected URLs when you need to inspect
the rendered source page before citing or synthesizing.

## Universal Agents Shell Behavior

Before using a shell fallback in Universal Agents, load
`shell-execution-workflows`. Pass the underlying command without an `rtk`
prefix; the shell tool selects RTK rewrite or proxy mode automatically. Use an
explicit timeout for HTTP calls and inspect the separate output/error,
termination reason, RTK mode, and warning fields.

In Universal Agents the Brave key is never in any environment, so `curl` in
the shell cannot authenticate to Brave. Use the artifact tools. For a Brave
endpoint they do not cover, send a brokered request instead:
`secure_cli(provider="secure_requests", action="get", params={"url":
"https://api.search.brave.com/res/v1/..."})`. It belongs to the built-in web
API tool `http:brave-search`; the request carries no key and no `${...}`
placeholder, and the broker adds the linked key in the `X-Subscription-Token`
header. Never put a key in a command string.

## Credential Handling

In Universal Agents the Brave key is the linked account of `http:brave-search`
in the credential store: the person's own key first, then the team's while
the team shares Brave Search (the default; `/accounts` shows it). Onboarding
saves the Brave key typed there as the team's key. The artifact
tools and brokered requests send no key; the broker adds it. `http:brave-search`
is part of internet access, so agents need no grant unless someone blocked it.

Do not ask the user to paste Brave API keys into chat, code, or command
examples. If a Brave tool reports `account_link_missing`, tell the user that a
team administrator links the team's key with `/link http:brave-search team`,
or that they can link their own with `/link http:brave-search`; when the team
keeps Brave Search private, only their own key is used, so they link their
own. Then retry. If
it reports `access_denied`, someone blocked Brave for this work: use another
search provider and say so. `BRAVE_SEARCH_API_KEY` is not a Universal Agents
setting (startup refuses it); the shell examples below are only for running
outside Universal Agents with your own key in that variable.

## Brave Web Search

Use web search for ranked links, snippets, result comparison, source discovery,
and custom ranking.

Endpoint:

```http
GET https://api.search.brave.com/res/v1/web/search
```

Common parameters:

- `q`: required query text.
- `count`: 1 to 20 web results.
- `offset`: 0 to 9 for pagination.
- `country`: 2-letter country code, default `US`.
- `search_lang`: result language, default `en`.
- `safesearch`: `off`, `moderate`, or `strict`.
- `freshness`: `pd`, `pw`, `pm`, `py`, or `YYYY-MM-DDtoYYYY-MM-DD`.
- `result_filter`: comma-separated result types such as `web`, `news`, or
  `discussions`.
- `goggles`: hosted Goggle URL or inline Goggle rules.

Shell fallback outside Universal Agents only:

```bash
curl -s "https://api.search.brave.com/res/v1/web/search" \
  -H "Accept: application/json" \
  -H "X-Subscription-Token: ${BRAVE_SEARCH_API_KEY}" \
  -G \
  --data-urlencode "q=rust programming tutorials" \
  --data-urlencode "country=US" \
  --data-urlencode "search_lang=en" \
  --data-urlencode "count=10" \
  --data-urlencode "safesearch=moderate" \
  --data-urlencode "freshness=pm"
```

## Brave LLM Context

Use LLM Context when the intended consumer is an agent or model and the task
needs extracted grounding context, not just links and snippets.

Endpoint:

```http
GET https://api.search.brave.com/res/v1/llm/context
```

Common parameters:

- `q`: required query text.
- `count`: 1 to 50 search results considered.
- `maximum_number_of_urls`: 1 to 50 URLs in returned context.
- `maximum_number_of_tokens`: 1024 to 32768 approximate context tokens.
- `maximum_number_of_snippets`: 1 to 256 snippets.
- `context_threshold_mode`: `strict`, `balanced`, `lenient`, or `disabled`.
- `freshness`: `pd`, `pw`, `pm`, `py`, or a custom date range.

Shell fallback outside Universal Agents only:

```bash
curl -s "https://api.search.brave.com/res/v1/llm/context" \
  -H "Accept: application/json" \
  -H "X-Subscription-Token: ${BRAVE_SEARCH_API_KEY}" \
  -G \
  --data-urlencode "q=search API for grounding LLMs" \
  --data-urlencode "count=20" \
  --data-urlencode "maximum_number_of_urls=8" \
  --data-urlencode "maximum_number_of_tokens=8192"
```

## Output Discipline

When returning research results:

- Cite source URLs for important claims.
- State which provider or providers were used.
- If multiple searches disagree, summarize the conflict instead of forcing a
  false consensus.
- Keep raw JSON and large page content in artifacts; return only compact
  findings, source links, and the reasoning-relevant differences.
