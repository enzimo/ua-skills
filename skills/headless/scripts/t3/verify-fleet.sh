#!/bin/bash
# verify-fleet.sh - verify T3 Code, installed coding-agent CLIs, service
# status, and bidirectional T3 environment links across local and remote hosts.
#
# usage:
#   verify-fleet.sh DIR --platform mac|linux|windows [--clis t3,claude,codex,agy]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIR="${1:?usage: verify-fleet.sh DIR --platform mac|linux|windows [--clis t3,claude,codex,agy]}"
shift

PLATFORM=""
CLIS="t3,claude,codex,agy"

while [ $# -gt 0 ]; do
  case "$1" in
    --platform) PLATFORM="${2-}"; shift 2 ;;
    --clis) CLIS="${2-}"; shift 2 ;;
    *) echo "headless: unknown option $1" >&2; exit 1 ;;
  esac
done

case "$PLATFORM" in
  mac) . "$SCRIPT_DIR/../mac/lib.sh" ;;
  linux) . "$SCRIPT_DIR/../linux/lib.sh" ;;
  windows) . "$SCRIPT_DIR/../windows/lib.sh" ;;
  *) echo "headless: --platform must be mac, linux, or windows" >&2; exit 1 ;;
esac

IFS=',' read -r -a CLI_LIST <<< "$CLIS"
for cli in "${CLI_LIST[@]}"; do
  case "$cli" in
    t3 | claude | codex | agy) ;;
    *) die "unknown CLI '$cli'; supported CLIs are t3, claude, codex, agy" ;;
  esac
done

load_config "$DIR"
need_key

fails=0
check() { if [ "$1" = ok ]; then echo "ok    $2"; else echo "FAIL  $2"; fails=$((fails + 1)); fi; }

say "checking remote T3 fleet components on $ADDRESS ($PLATFORM)"
if [ "$PLATFORM" = windows ]; then
  out="$(win_ps "
foreach (\$c in @($(printf "'%s'," "${CLI_LIST[@]}" | sed 's/,$//'))) {
  if (Get-Command \$c -ErrorAction SilentlyContinue) {
    Write-Output ('ok    remote CLI ' + \$c + ': ' + (& \$c --version 2>&1 | Select-Object -First 1))
  } else {
    Write-Output ('FAIL  remote CLI ' + \$c + ': missing')
  }
}
if (Get-Command t3 -ErrorAction SilentlyContinue) {
  t3 status --json | Out-Null
  if (\$LASTEXITCODE -eq 0) { Write-Output 'ok    remote t3 status' } else { Write-Output 'FAIL  remote t3 status' }
  Write-Output '--- remote t3 environment list ---'
  t3 environment list
}
" | tr -d '\r')"
else
  out="$(on "export PATH=\"\$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH\"
for c in ${CLI_LIST[*]}; do
  if command -v \"\$c\" >/dev/null 2>&1; then
    printf 'ok    remote CLI %s: %s\n' \"\$c\" \"\$(\"\$c\" --version 2>&1 | head -n 1)\"
  else
    printf 'FAIL  remote CLI %s: missing\n' \"\$c\"
  fi
done
if command -v t3 >/dev/null 2>&1; then
  if t3 status --json >/dev/null 2>&1; then
    echo 'ok    remote t3 status'
  else
    echo 'FAIL  remote t3 status'
  fi
  echo '--- remote t3 environment list ---'
  t3 environment list || echo 'FAIL  remote t3 environment list'
fi")"
fi

printf '%s\n' "$out"
fails=$((fails + $(printf '%s\n' "$out" | grep -c '^FAIL' || true)))

if command -v t3 > /dev/null 2>&1; then
  echo "--- local t3 environment list ---"
  if t3 environment list; then
    check ok "local t3 environment list"
  else
    check fail "local t3 environment list"
  fi
else
  check fail "local t3 CLI missing on PATH"
fi

[ "$fails" -eq 0 ] || die "$fails T3 fleet check(s) failed"
say "T3 fleet checks passed"
