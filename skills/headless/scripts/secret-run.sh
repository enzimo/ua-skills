#!/bin/bash
# secret-run.sh - run a command with one secret on a file descriptor, read
# straight from the user's secret store. The secret never reaches a command
# line, an environment variable of this script, a file or this script's
# output; the agent only ever names the store entry.
#
# usage: secret-run.sh [--fd N] REF -- COMMAND [ARG...]
#
# COMMAND runs with the secret readable on descriptor N (default 3), then
# end of file. For two secrets, nest it:
#   secret-run.sh REF1 -- secret-run.sh --fd 4 REF2 -- COMMAND
#
# REF names where the secret lives:
#   av:NAME                 Automic Vault (av inject --mode=fd); asks for approval
#   op:op://VAULT/ITEM/FIELD
#                           1Password CLI (op read), signed in (passwords, keys, tokens)
#   bw:ITEM                 Bitwarden CLI login password (bw get password), unlocked
#   bw-notes:ITEM           Bitwarden CLI secure note / multi-line secret (bw get notes)
#   bw-ssh:ITEM             Bitwarden CLI SSH key item private key (bw get item)
#   bw-field:ITEM:FIELD     Bitwarden CLI custom field value (bw get item)
#   cmd:COMMAND             any command that prints the secret, run with sh -c
#   env:FILE:VAR            a KEY=value file only you may read (mode 600 or
#                           stricter, owned by you); last resort outside UA,
#                           see references/secrets.md
#   ua:KEY                  refused in unbrokered shell; Universal Agents keeps
#                           Sealbox/catalog secrets inside the broker
set -euo pipefail

die() { echo "secret-run: $*" >&2; exit 2; }

fd=3
if [ "${1-}" = --fd ]; then
  fd="${2-}"
  shift 2
fi
[[ "$fd" =~ ^[3-9]$ ]] || die "--fd takes a descriptor from 3 to 9"
ref="${1-}"
[ "${2-}" = -- ] || die "usage: secret-run.sh [--fd N] REF -- COMMAND [ARG...]"
shift 2
[ $# -gt 0 ] || die "no command to run"

json_extract_bw_ssh() {
  if command -v jq > /dev/null; then
    jq -r '.sshKey.privateKey // .notes // empty'
  elif command -v python3 > /dev/null; then
    python3 -c 'import json, sys; d = json.load(sys.stdin); v = (d.get("sshKey") or {}).get("privateKey") or d.get("notes") or ""; sys.stdout.write(v)'
  else
    die "bw-ssh: requires jq or python3 to read the Bitwarden item JSON"
  fi
}

json_extract_bw_field() {
  local field_name="$1"
  if command -v jq > /dev/null; then
    jq -r --arg name "$field_name" '(.fields // [])[] | select(.name == $name) | .value' | head -n 1
  elif command -v python3 > /dev/null; then
    python3 - "$field_name" <<'PY'
import json, sys
target = sys.argv[1]
data = json.load(sys.stdin)
for f in data.get("fields") or []:
    if f.get("name") == target and f.get("value") is not None:
        sys.stdout.write(str(f["value"]))
        break
PY
  else
    die "bw-field: requires jq or python3 to read the Bitwarden item JSON"
  fi
}

case "$ref" in
  ua:*)
    die "ua: credentials belong to the Universal Agents broker and cannot be read from a local shell; use secure_cli / brokered execution (see references/universal-agents.md)"
    ;;
  av:*)
    name="${ref#av:}"
    [[ "$name" =~ ^[A-Za-z_][A-Za-z0-9_.-]*$ ]] || die "av: needs a secret name"
    command -v av > /dev/null || die "the av command (Automic Vault) is not installed"
    exec av inject --mode=fd "+$name:$fd" -- "$@"
    ;;
  op:*)
    item="${ref#op:}"
    [[ "$item" == op://* ]] || die "op: needs an op://VAULT/ITEM/FIELD reference"
    command -v op > /dev/null || die "the op command (1Password CLI) is not installed"
    produce() { op read --no-newline "$item"; }
    ;;
  bw:*)
    item="${ref#bw:}"
    [ -n "$item" ] || die "bw: needs an item name or id"
    command -v bw > /dev/null || die "the bw command (Bitwarden CLI) is not installed"
    produce() { bw get password "$item"; }
    ;;
  bw-notes:*)
    item="${ref#bw-notes:}"
    [ -n "$item" ] || die "bw-notes: needs an item name or id"
    command -v bw > /dev/null || die "the bw command (Bitwarden CLI) is not installed"
    produce() { bw get notes "$item"; }
    ;;
  bw-ssh:*)
    item="${ref#bw-ssh:}"
    [ -n "$item" ] || die "bw-ssh: needs an item name or id"
    command -v bw > /dev/null || die "the bw command (Bitwarden CLI) is not installed"
    produce() { bw get item "$item" | json_extract_bw_ssh; }
    ;;
  bw-field:*)
    rest="${ref#bw-field:}"
    item="${rest%:*}"
    field="${rest##*:}"
    [ "$item" != "$rest" ] && [ -n "$item" ] && [ -n "$field" ] || die "bw-field: needs ITEM:FIELD"
    command -v bw > /dev/null || die "the bw command (Bitwarden CLI) is not installed"
    produce() { bw get item "$item" | json_extract_bw_field "$field"; }
    ;;
  cmd:*)
    producer="${ref#cmd:}"
    [ -n "$producer" ] || die "cmd: needs a command"
    produce() { /bin/sh -c "$producer"; }
    ;;
  env:*)
    rest="${ref#env:}"
    file="${rest%:*}"
    var="${rest##*:}"
    [ "$file" != "$rest" ] || die "env: needs FILE:VAR"
    [[ "$var" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die "env: VAR is not a variable name"
    case "$file" in "~/"*) file="$HOME/${file#\~/}" ;; esac
    [ -f "$file" ] || die "env: $file does not exist"
    [ -O "$file" ] || die "env: $file is not yours"
    if [ -n "$(find "$file" -prune \( -perm -040 -o -perm -020 -o -perm -004 -o -perm -002 \))" ]; then
      die "env: $file can be read by others; run chmod 600 on it"
    fi
    grep -q "^$var=" "$file" || die "env: $file has no $var line"
    produce() {
      sed -n "s/^$var=//p" "$file" | head -n 1 \
        | sed -e "s/^\"\\(.*\\)\"\$/\\1/" -e "s/^'\\(.*\\)'\$/\\1/" | tr -d '\n'
    }
    ;;
  *) die "unknown store in '$ref'; use av:, op:, bw:, bw-notes:, bw-ssh:, bw-field:, cmd: or env:" ;;
esac

# The secret goes through a pipe, never through this script's variables.
eval "exec $fd< <(produce)"
exec "$@"
