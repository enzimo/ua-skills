#!/bin/bash
# link-fleet.sh - bidirectionally link the local T3 Code environment and a
# headless remote T3 Code environment without printing pairing codes to stdout,
# stderr, or agent logs.
#
# usage:
#   link-fleet.sh DIR --platform mac|linux|windows
#     [--direction both|remote-to-local|local-to-remote]
#     [--access approval-required]
#     [--transport tailscale|connect|lan]
#     [--remote-url URL]
#     [--local-url URL]
#     [--ttl 5m]
#
# Prefer --transport tailscale (uses `t3 pair --tailscale` over Tailscale Serve
# HTTPS). Pairing tokens are piped strictly between `t3 pair` and
# `t3 environment link --from -` inside memory/pipes and never printed.
set -euo pipefail
set +x

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIR="${1:?usage: link-fleet.sh DIR --platform mac|linux|windows [--direction both|remote-to-local|local-to-remote] [--access approval-required] [--transport tailscale|connect|lan]}"
shift

PLATFORM=""
DIRECTION="both"
ACCESS="approval-required"
TRANSPORT="tailscale"
REMOTE_URL=""
LOCAL_URL=""
TTL="5m"

while [ $# -gt 0 ]; do
  case "$1" in
    --platform) PLATFORM="${2-}"; shift 2 ;;
    --direction) DIRECTION="${2-}"; shift 2 ;;
    --access) ACCESS="${2-}"; shift 2 ;;
    --transport) TRANSPORT="${2-}"; shift 2 ;;
    --remote-url) REMOTE_URL="${2-}"; shift 2 ;;
    --local-url) LOCAL_URL="${2-}"; shift 2 ;;
    --ttl) TTL="${2-}"; shift 2 ;;
    *) echo "headless: unknown option $1" >&2; exit 1 ;;
  esac
done

case "$PLATFORM" in
  mac) . "$SCRIPT_DIR/../mac/lib.sh" ;;
  linux) . "$SCRIPT_DIR/../linux/lib.sh" ;;
  windows) . "$SCRIPT_DIR/../windows/lib.sh" ;;
  *) echo "headless: --platform must be mac, linux, or windows" >&2; exit 1 ;;
esac

case "$DIRECTION" in
  both | remote-to-local | local-to-remote) ;;
  *) die "--direction must be both, remote-to-local, or local-to-remote" ;;
esac

case "$ACCESS" in
  read-only | approval-required | auto-accept-edits | auto | full-access) ;;
  *) die "--access must be read-only, approval-required, auto-accept-edits, auto, or full-access" ;;
esac

case "$TRANSPORT" in
  tailscale | connect | lan) ;;
  *) die "--transport must be tailscale, connect, or lan" ;;
esac

[[ "$TTL" =~ ^[0-9]+[smhd]$ ]] || die "--ttl must look like 5m or 15m"
[ -z "$REMOTE_URL" ] || [[ "$REMOTE_URL" =~ ^https?://[A-Za-z0-9.:/_-]+$ ]] || die "--remote-url must be an http(s) URL"
[ -z "$LOCAL_URL" ] || [[ "$LOCAL_URL" =~ ^https?://[A-Za-z0-9.:/_-]+$ ]] || die "--local-url must be an http(s) URL"

command -v t3 > /dev/null || die "local t3 CLI is not installed on PATH"
command -v python3 > /dev/null || die "python3 is required to parse pairing output without echoing secrets"

load_config "$DIR"
need_key

# Parse `t3 pair` output from stdin into one "<base_url> <pairing_code>" line
# without echoing raw output on error.
parse_pair_line() {
  local fallback_url="$1"
  python3 - "$fallback_url" <<'PY'
import re, sys
from urllib.parse import urlparse, parse_qs

fallback_url = sys.argv[1].strip()
text = sys.stdin.read()

url = ""
code = ""

# 1. Look for a pairing URL carrying #token=... or ?token=...
for match in re.finditer(r"https?://[^\s'\"<>]+", text):
    candidate = match.group(0).rstrip(".,);")
    parsed = urlparse(candidate)
    frag = parse_qs(parsed.fragment)
    qs = parse_qs(parsed.query)
    tok = (frag.get("token") or qs.get("token") or frag.get("code") or qs.get("code") or [""])[0]
    base = f"{parsed.scheme}://{parsed.netloc}"
    if tok:
        url = base
        code = tok
        break
    if not url and parsed.netloc:
        url = base

# 2. Fall back to labeled code line if token was printed separately
if not code:
    m = re.search(r"(?:pairing\s+code|code|token)\s*[:=]\s*([A-Za-z0-9._~+/=-]{8,})", text, re.I)
    if m:
        code = m.group(1)

if not url:
    url = fallback_url

if not url or not code:
    sys.exit(1)

sys.stdout.write(f"{url} {code}\n")
PY
}

pair_flags="--ttl $TTL"
if [ "$TRANSPORT" = tailscale ]; then
  pair_flags="$pair_flags --tailscale"
fi

LOCAL_LABEL="$(hostname -s 2> /dev/null || hostname || echo local-t3)"
REMOTE_LABEL="$(basename "$CONFIG")"

run_remote_pair() {
  if [ "$PLATFORM" = windows ]; then
    win_ps "t3 pair $pair_flags --label '$LOCAL_LABEL'" 2> /dev/null | tr -d '\r'
  else
    on "export PATH=\"\$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH\"; t3 pair $pair_flags --label '$LOCAL_LABEL'" 2> /dev/null
  fi
}

run_remote_link_from_stdin() {
  if [ "$PLATFORM" = windows ]; then
    win_ps "[Console]::In.ReadToEnd() | t3 environment link --from - --access '$ACCESS'"
  else
    on "export PATH=\"\$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH\"; t3 environment link --from - --access '$ACCESS'"
  fi
}

if [ "$DIRECTION" = both ] || [ "$DIRECTION" = remote-to-local ]; then
  say "linking remote T3 environment ($REMOTE_LABEL) into local T3 Code (access=$ACCESS)"
  pair_line="$(run_remote_pair | parse_pair_line "$REMOTE_URL")" \
    || die "could not extract pairing link from remote 't3 pair'; verify T3 Code and Tailscale Serve are running on $ADDRESS or link via the T3 Code card (t3_environment_link)"
  printf '%s\n' "$pair_line" | t3 environment link --from - --access "$ACCESS"
  unset pair_line
  say "linked remote ($REMOTE_LABEL) into local T3 Code"
fi

if [ "$DIRECTION" = both ] || [ "$DIRECTION" = local-to-remote ]; then
  say "linking local T3 environment ($LOCAL_LABEL) into remote T3 Code ($REMOTE_LABEL, access=$ACCESS)"
  pair_line="$(t3 pair $pair_flags --label "$REMOTE_LABEL" 2> /dev/null | parse_pair_line "$LOCAL_URL")" \
    || die "could not extract pairing link from local 't3 pair'; verify local T3 Code server is running and reachable over $TRANSPORT"
  printf '%s\n' "$pair_line" | run_remote_link_from_stdin
  unset pair_line
  say "linked local ($LOCAL_LABEL) into remote T3 Code ($REMOTE_LABEL)"
fi

say "T3 fleet linking complete ($DIRECTION)"
