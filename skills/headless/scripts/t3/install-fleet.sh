#!/bin/bash
# install-fleet.sh - install T3 Code and coding-agent CLIs on a headless
# machine over its verified key-only SSH connection, and configure the T3
# background service for fleet integration.
#
# usage:
#   install-fleet.sh DIR --platform mac|linux|windows
#     [--clis t3,claude,codex,agy]
#     [--transport tailscale|connect|lan|none]
#     [--protect-service]
#
# Every install step is idempotent: already-installed CLIs are kept and
# reported with their versions.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIR="${1:?usage: install-fleet.sh DIR --platform mac|linux|windows [--clis t3,claude,codex,agy] [--transport tailscale|connect|lan|none] [--protect-service]}"
shift

PLATFORM=""
CLIS="t3,claude,codex,agy"
TRANSPORT="tailscale"
PROTECT=false

while [ $# -gt 0 ]; do
  case "$1" in
    --platform) PLATFORM="${2-}"; shift 2 ;;
    --clis) CLIS="${2-}"; shift 2 ;;
    --transport) TRANSPORT="${2-}"; shift 2 ;;
    --protect-service) PROTECT=true; shift ;;
    *) echo "headless: unknown option $1" >&2; exit 1 ;;
  esac
done

case "$PLATFORM" in
  mac) . "$SCRIPT_DIR/../mac/lib.sh" ;;
  linux) . "$SCRIPT_DIR/../linux/lib.sh" ;;
  windows) . "$SCRIPT_DIR/../windows/lib.sh" ;;
  *) echo "headless: --platform must be mac, linux, or windows" >&2; exit 1 ;;
esac

case "$TRANSPORT" in
  tailscale | connect | lan | none) ;;
  *) die "--transport must be tailscale, connect, lan, or none" ;;
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

if [ "$PROTECT" = true ]; then
  [ "$PLATFORM" = linux ] || die "--protect-service is only supported on Linux with systemd"
  set -- "$CONFIG" --platform "$PLATFORM" --clis "$CLIS" --transport "$TRANSPORT" --protect-service
  with_secrets "$@"
  read_password
fi

if [ "$PLATFORM" = windows ]; then
  ps_clis=""
  for cli in "${CLI_LIST[@]}"; do
    case "$cli" in
      t3)
        ps_clis="$ps_clis
if (-not (Get-Command t3 -ErrorAction SilentlyContinue)) { irm https://t3.codes/install.ps1 | iex }
" ;;
      claude)
        ps_clis="$ps_clis
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { irm https://claude.ai/install.ps1 | iex }
" ;;
      codex)
        ps_clis="$ps_clis
if (-not (Get-Command codex -ErrorAction SilentlyContinue)) { irm https://chatgpt.com/codex/install.ps1 | iex }
" ;;
      agy)
        ps_clis="$ps_clis
if (-not (Get-Command agy -ErrorAction SilentlyContinue)) { irm https://antigravity.google/cli/install.ps1 | iex }
" ;;
    esac
  done

  ps_service=""
  case "$TRANSPORT" in
    tailscale) ps_service="t3 service install" ;;
    connect) ps_service="t3 up --connect --headless" ;;
    lan) ps_service="t3 up --lan --yes" ;;
    none) ps_service="" ;;
  esac

  say "installing T3 fleet CLIs ($CLIS) on $ADDRESS (windows)"
  win_ps "
\$ErrorActionPreference = 'Stop'
$ps_clis
\$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
$ps_service
foreach (\$c in @($(printf "'%s'," "${CLI_LIST[@]}" | sed 's/,$//'))) {
  if (Get-Command \$c -ErrorAction SilentlyContinue) {
    Write-Output (\"ok    \" + \$c + \": \" + (& \$c --version 2>&1 | Select-Object -First 1))
  } else {
    Write-Output (\"FAIL  \" + \$c + \": not on PATH\")
  }
}
"
  say "T3 fleet setup step finished on $ADDRESS"
  exit 0
fi

# macOS and Linux
say "installing T3 fleet CLIs ($CLIS) on $ADDRESS ($PLATFORM)"
remote_script='
set -euo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p "$HOME/.local/bin"
for rc in "$HOME/.profile" "$HOME/.bashrc" "$HOME/.zshrc"; do
  if [ -f "$rc" ] && ! grep -qF ".local/bin" "$rc"; then
    printf "\nexport PATH=\"\$HOME/.local/bin:\$PATH\"\n" >> "$rc"
  fi
done
'

for cli in "${CLI_LIST[@]}"; do
  case "$cli" in
    t3)
      remote_script="$remote_script
if ! command -v t3 >/dev/null 2>&1; then
  curl -fsSL https://t3.codes/install.sh | sh
fi
" ;;
    claude)
      remote_script="$remote_script
if ! command -v claude >/dev/null 2>&1; then
  curl -fsSL https://claude.ai/install.sh | bash
fi
" ;;
    codex)
      remote_script="$remote_script
if ! command -v codex >/dev/null 2>&1; then
  curl -fsSL https://chatgpt.com/codex/install.sh | sh
fi
" ;;
    agy)
      remote_script="$remote_script
if ! command -v agy >/dev/null 2>&1; then
  curl -fsSL https://antigravity.google/cli/install.sh | bash
fi
" ;;
  esac
done

case "$TRANSPORT" in
  tailscale)
    remote_script="$remote_script
t3 service install
" ;;
  connect)
    remote_script="$remote_script
t3 up --connect --headless
" ;;
  lan)
    remote_script="$remote_script
t3 up --lan --yes
" ;;
  none) ;;
esac

remote_script="$remote_script
for c in ${CLI_LIST[*]}; do
  if command -v \"\$c\" >/dev/null 2>&1; then
    printf 'ok    %s: %s\n' \"\$c\" \"\$(\"\$c\" --version 2>&1 | head -n 1)\"
  else
    printf 'FAIL  %s: not on PATH\n' \"\$c\"
  fi
done
"

printf '%s\n' "$remote_script" | on '/bin/bash -s'

if [ "$PROTECT" = true ]; then
  say "protecting T3 Code service from agent OOM kills on $ADDRESS"
  as_root '/usr/bin/env bash -lc "export PATH=\$HOME/.local/bin:/usr/local/bin:\$PATH; t3 service protect"'
  unset PASSWORD
fi

say "T3 fleet setup step finished on $ADDRESS"
