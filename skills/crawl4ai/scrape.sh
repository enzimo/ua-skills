#!/usr/bin/env bash
# scrape.sh — thin CLI over a configurable Crawl4AI service
#
# Requires: bash, curl, jq
#
# Usage:
#   scrape.sh md   <url> [-q QUERY] [-f raw|fit|bm25|llm] [--fresh]
#   scrape.sh html <url> [--fresh]
#   scrape.sh crawl <url> [<url> ...] [-q QUERY] [--css SCHEMA_JSON_FILE]
#                         [--screenshot] [--pdf] [--fresh] [--raw]
#   scrape.sh stream <url> [<url> ...] [options as in crawl]
#   scrape.sh deep <root_url> [--depth N] [--max N] [--include-pattern PAT]
#                             [--domain DOMAIN] [-q QUERY]
#   scrape.sh js <url> --code 'JS;JS;...'
#   scrape.sh screenshot <url> -o file.png
#   scrape.sh pdf        <url> -o file.pdf
#   scrape.sh health
#
# Output:
#   By default prints fit_markdown to stdout. Use --raw to get full JSON.
#
# Env:
#   CRAWL4AI_BASE   override base URL (default http://127.0.0.1:11235)

set -euo pipefail

BASE="${CRAWL4AI_BASE:-http://127.0.0.1:11235}"

die() { echo "error: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "missing dependency: $1"; }
need curl; need jq

usage() { sed -n '2,30p' "$0"; exit 1; }

post() {
  # post <path> <json>
  curl -fsS -X POST "$BASE$1" \
    -H 'Content-Type: application/json' \
    --data-binary "$2"
}

post_stream() {
  curl -fsS -N -X POST "$BASE$1" \
    -H 'Content-Type: application/json' \
    --data-binary "$2"
}

cmd="${1:-}"; shift || usage

case "$cmd" in

  health)
    curl -fsS "$BASE/health" | jq .
    ;;

  md)
    url="${1:-}"; shift || die "url required"
    query=null; filter='"fit"'; cache='"0"'; raw=0
    while [[ $# -gt 0 ]]; do
      case "$1" in
        -q) query=$(jq -Rn --arg v "$2" '$v'); filter='"bm25"'; shift 2 ;;
        -f) filter=$(jq -Rn --arg v "$2" '$v'); shift 2 ;;
        --fresh) cache='"1"'; shift ;;
        --raw)   raw=1; shift ;;
        *) die "unknown flag: $1" ;;
      esac
    done
    body=$(jq -nc --arg url "$url" \
              --argjson f "$filter" --argjson q "$query" --argjson c "$cache" \
              '{url:$url,f:$f,q:$q,c:$c}')
    resp=$(post /md "$body")
    if [[ $raw -eq 1 ]]; then echo "$resp" | jq .
    else echo "$resp" | jq -r '.markdown'
    fi
    ;;

  html)
    url="${1:-}"; shift || die "url required"
    cache='"0"'
    [[ "${1:-}" == "--fresh" ]] && cache='"1"'
    body=$(jq -nc --arg url "$url" --argjson c "$cache" '{url:$url,c:$c}')
    post /html "$body" | jq -r '.html // .'
    ;;

  crawl|stream)
    [[ $# -ge 1 ]] || die "at least one url required"
    urls_json='[]'; query=""; css_file=""; want_shot=0; want_pdf=0
    cache_mode="BYPASS"; raw=0
    # collect urls until first flag
    while [[ $# -gt 0 && "$1" != -* ]]; do
      urls_json=$(jq -c --arg u "$1" '. + [$u]' <<<"$urls_json"); shift
    done
    while [[ $# -gt 0 ]]; do
      case "$1" in
        -q) query="$2"; shift 2 ;;
        --css) css_file="$2"; shift 2 ;;
        --screenshot) want_shot=1; shift ;;
        --pdf) want_pdf=1; shift ;;
        --fresh) cache_mode="BYPASS"; shift ;;
        --cache) cache_mode="ENABLED"; shift ;;
        --raw) raw=1; shift ;;
        *) die "unknown flag: $1" ;;
      esac
    done

    # build content_filter
    if [[ -n "$query" ]]; then
      cfilter=$(jq -nc --arg q "$query" \
        '{type:"BM25ContentFilter",params:{user_query:$q,bm25_threshold:1.2}}')
    else
      cfilter=$(jq -nc \
        '{type:"PruningContentFilter",params:{threshold:0.48,threshold_type:"dynamic",min_word_threshold:10}}')
    fi

    mdgen=$(jq -nc --argjson cf "$cfilter" '{
      type:"DefaultMarkdownGenerator",
      params:{ options:{ignore_images:true, body_width:0}, content_filter:$cf }
    }')

    crawler_params=$(jq -nc \
      --arg cache "$cache_mode" \
      --argjson mdgen "$mdgen" \
      --argjson shot $want_shot --argjson pdf $want_pdf '{
        cache_mode:$cache,
        word_count_threshold:15,
        excluded_tags:["nav","footer","header","aside","form"],
        exclude_external_links:true,
        exclude_social_media_links:true,
        remove_overlay_elements:true,
        wait_until:"domcontentloaded",
        page_timeout:30000,
        screenshot:($shot==1),
        pdf:($pdf==1),
        markdown_generator:$mdgen
      }')

    if [[ -n "$css_file" ]]; then
      [[ -f "$css_file" ]] || die "css schema file not found: $css_file"
      schema=$(cat "$css_file")
      crawler_params=$(jq -c --argjson s "$schema" \
        '. + {extraction_strategy:{type:"JsonCssExtractionStrategy",params:{schema:$s}}}' \
        <<<"$crawler_params")
    fi

    body=$(jq -nc --argjson urls "$urls_json" --argjson cp "$crawler_params" '{
      urls:$urls,
      browser_config:{type:"BrowserConfig",params:{headless:true,user_agent_mode:"random"}},
      crawler_config:{type:"CrawlerRunConfig",params:$cp}
    }')

    if [[ "$cmd" == "stream" ]]; then
      if [[ $raw -eq 1 ]]; then post_stream /crawl/stream "$body"
      else post_stream /crawl/stream "$body" | \
           jq -r 'if .markdown.fit_markdown then "\n\n=== \(.url) ===\n\n" + .markdown.fit_markdown else . | tostring end'
      fi
    else
      resp=$(post /crawl "$body")
      if [[ $raw -eq 1 ]]; then echo "$resp" | jq .
      else echo "$resp" | jq -r '.results[] | "\n\n=== \(.url) ===\n\n" + (.markdown.fit_markdown // .markdown.raw_markdown // "")'
      fi
    fi
    ;;

  deep)
    root="${1:-}"; shift || die "root url required"
    depth=2; maxp=50; pat=""; dom=""; query=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --depth) depth="$2"; shift 2 ;;
        --max)   maxp="$2"; shift 2 ;;
        --include-pattern) pat="$2"; shift 2 ;;
        --domain) dom="$2"; shift 2 ;;
        -q) query="$2"; shift 2 ;;
        *) die "unknown flag: $1" ;;
      esac
    done

    filters='[]'
    if [[ -n "$dom" ]]; then
      filters=$(jq -c --arg d "$dom" \
        '. + [{type:"DomainFilter",params:{allowed_domains:[$d]}}]' <<<"$filters")
    fi
    if [[ -n "$pat" ]]; then
      filters=$(jq -c --arg p "$pat" \
        '. + [{type:"URLPatternFilter",params:{patterns:[$p]}}]' <<<"$filters")
    fi
    filters=$(jq -c \
      '. + [{type:"ContentTypeFilter",params:{allowed_types:["text/html"]}}]' \
      <<<"$filters")

    if [[ -n "$query" ]]; then
      cfilter=$(jq -nc --arg q "$query" \
        '{type:"BM25ContentFilter",params:{user_query:$q,bm25_threshold:1.2}}')
    else
      cfilter=$(jq -nc \
        '{type:"PruningContentFilter",params:{threshold:0.5,threshold_type:"dynamic",min_word_threshold:15}}')
    fi

    body=$(jq -nc \
      --arg root "$root" \
      --argjson depth "$depth" --argjson maxp "$maxp" \
      --argjson filters "$filters" --argjson cf "$cfilter" '{
        urls:[$root],
        browser_config:{type:"BrowserConfig",params:{headless:true,user_agent_mode:"random"}},
        crawler_config:{type:"CrawlerRunConfig",params:{
          cache_mode:"BYPASS", stream:true,
          excluded_tags:["nav","footer","header","aside","form"],
          exclude_external_links:true, remove_overlay_elements:true,
          wait_until:"domcontentloaded", page_timeout:30000,
          markdown_generator:{type:"DefaultMarkdownGenerator",params:{
            options:{ignore_images:true, body_width:0}, content_filter:$cf
          }},
          deep_crawl_strategy:{type:"BFSDeepCrawlStrategy",params:{
            max_depth:$depth, max_pages:$maxp, include_external:false,
            filter_chain:{type:"FilterChain",params:{filters:$filters}}
          }}
        }}
      }')

    post_stream /crawl/stream "$body" | \
      jq -r 'if .markdown.fit_markdown then "\n\n=== \(.url) ===\n\n" + .markdown.fit_markdown else empty end'
    ;;

  js)
    url="${1:-}"; shift || die "url required"
    code=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --code) code="$2"; shift 2 ;;
        *) die "unknown flag: $1" ;;
      esac
    done
    [[ -n "$code" ]] || die "--code required"
    # split on ';' into array, trim
    snippets=$(jq -Rc 'split(";") | map(gsub("^\\s+|\\s+$";"")) | map(select(length>0))' <<<"$code")
    body=$(jq -nc --arg url "$url" --argjson s "$snippets" \
      '{url:$url, scripts:$s}')
    post /execute_js "$body" | jq .
    ;;

  screenshot)
    url="${1:-}"; shift || die "url required"
    out=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        -o) out="$2"; shift 2 ;;
        *) die "unknown flag: $1" ;;
      esac
    done
    [[ -n "$out" ]] || die "-o output file required"
    body=$(jq -nc --arg url "$url" '{url:$url}')
    post /screenshot "$body" | jq -r '.screenshot' | base64 -d > "$out"
    echo "wrote $out" >&2
    ;;

  pdf)
    url="${1:-}"; shift || die "url required"
    out=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        -o) out="$2"; shift 2 ;;
        *) die "unknown flag: $1" ;;
      esac
    done
    [[ -n "$out" ]] || die "-o output file required"
    body=$(jq -nc --arg url "$url" '{url:$url}')
    post /pdf "$body" | jq -r '.pdf' | base64 -d > "$out"
    echo "wrote $out" >&2
    ;;

  -h|--help|help|"") usage ;;
  *) die "unknown command: $cmd" ;;
esac
