---
name: bw
description: Use Bitwarden through the `bw` CLI or the brokered secure_cli Bitwarden action surface. Trigger when Codex needs Bitwarden auth, `BW_SESSION` handling, password-manager credential search, metadata lookup, or brokered secret use.
---

# Bitwarden CLI

`bw` is the Bitwarden command-line client. In this project, Bitwarden is
treated as a broker-owned password-manager integration: agents can search
credential metadata and ask the broker to use a secret for an allowlisted target
action, but raw secret values and Bitwarden session keys must stay out of agent
chat, memory, logs, and shell history.

## Brokered Runtime First

In Crew broker/openshell runtimes, agents must not run raw credentialed `bw`
commands through shell. Use `secure_cli` for allowlisted Bitwarden work. Direct
shell attempts for `gog`, `gh`, and `bw` are intentionally blocked.

Universal Agents enforces that block before RTK planning and also detects
nested shell attempts. The shared `shell-execution-workflows` skill documents
this policy boundary. Do not retry with an `rtk` prefix, `rtk proxy`, or
`sh -c`; use `secure_cli` and `secure-credential-workflows`.

Example shape:

```text
secure_cli(
  provider="bitwarden",
  action="credential.search",
  params={"query": "github", "limit": 10},
  reason="Find candidate GitHub credentials by metadata without exposing secrets."
)
```

Supported Bitwarden broker actions:

| Goal | Action | Params |
| --- | --- | --- |
| Search credential metadata | `credential.search` | optional `query`, `limit`, `include_archived` |
| Read one metadata record | `credential.get_metadata` | `item_id` or `item_name` |
| Use a secret for an allowlisted action | `credential.use_for_action` | `target_provider`, `target_action`, `item_id` or `item_name`, optional `field_ref`, `hostname` |

Compatibility aliases may be accepted by the broker, including
`credential.list`, `item_search_metadata`, `item_get_metadata`,
`use_secret_for_action`, and `github.auth.login.bitwarden`. Prefer canonical
action names in new work.

## Auth Handling

Before requesting new Bitwarden material, check whether broker auth or a direct
`bw` session is already hydrated for the runtime. Use `auth.status`-style
broker feedback when available and `bw status` only when direct shell use is
allowed.

Do not ask the user to paste Bitwarden credentials, passwords, API keys,
session keys, or vault exports into chat. If fresh credentials are needed,
direct the user to the credential collection form for Bitwarden:

When the broker reports Bitwarden auth is required, ask the user to run:

```text
/auth bitwarden
```

The current broker flow does not provide `/auth bitwarden web`. Bitwarden CLI
supports multiple login methods, including email/password, API key, and SSO, but
vault data still requires an unlocked session key. The broker therefore accepts
an unlocked `BW_SESSION` value and verifies it with `bw status`.

User-side setup in a trusted shell:

```bash
bw login
export BW_SESSION="$(bw unlock --raw)"
```

Then open the `/auth bitwarden` broker URL and paste only the session value into
the broker form. The credential is submitted directly to the secure broker and
is not sent to the agent.

For API-key or SSO login, the same unlock step is still required before vault
data can be used:

```bash
bw login --apikey
export BW_SESSION="$(bw unlock --raw)"
```

```bash
bw login --sso
export BW_SESSION="$(bw unlock --raw)"
```

If Bitwarden reports the vault is locked or the broker reports `auth_required`,
the session may be missing, expired, locked, logged out, or invalid for the
broker process. Ask the user to unlock again and resubmit through
`/auth bitwarden`.

## Common Broker Workflows

Search for credential metadata:

```text
secure_cli(
  provider="bitwarden",
  action="credential.search",
  params={"query": "github", "limit": 20},
  reason="Find matching Bitwarden items by metadata."
)
```

Get metadata for a selected item:

```text
secure_cli(
  provider="bitwarden",
  action="credential.get_metadata",
  params={"item_id": "BITWARDEN_ITEM_ID"},
  reason="Inspect non-secret metadata for the selected Bitwarden item."
)
```

Use a Bitwarden secret to authenticate GitHub inside the broker:

```text
secure_cli(
  provider="bitwarden",
  action="credential.use_for_action",
  params={
    "target_provider": "github",
    "target_action": "auth.login",
    "item_id": "BITWARDEN_ITEM_ID",
    "field_ref": "token",
    "hostname": "github.com"
  },
  reason="Use the selected broker-held Bitwarden token to authenticate gh."
)
```

Equivalent GitHub-provider form:

```text
secure_cli(
  provider="github",
  action="auth.login.credential",
  params={
    "credential_provider": "bitwarden",
    "item_id": "BITWARDEN_ITEM_ID",
    "field_ref": "token",
    "hostname": "github.com"
  },
  reason="Authenticate gh using a GitHub token stored in Bitwarden."
)
```

## Metadata Exposure Rules

Bitwarden `credential.search` and `credential.get_metadata` may expose refs,
display names, usernames, URLs, domains, folder IDs, tags, item types, revision
dates, secret field labels, and supported automations.

They must not expose passwords, tokens, TOTP values or seeds, secure notes, raw
custom-field values, `BW_SESSION`, broker tokens, or manager sessions. If tool
output includes secret material, treat it as a broker bug, stop using it, and
report the redaction failure.

## Raw bw Ground Rules

Use this section only when direct shell access to authenticated `bw` is
available and broker policy allows it.

- Start with `bw --help`, `bw status`, and command-specific `--help` when
  command shape or auth state is unclear.
- Prefer JSON-producing commands for agent work, such as `bw list items` and
  `bw get item <id-or-name>`.
- Use `--session <value>` only in a trusted local shell. Do not place session
  keys in prompts, task notes, code, tests, or committed files.
- Use `BW_SESSION_FILE` or broker-owned secret files for runtime wiring when
  the repo supports it; avoid durable plaintext shell profiles.
- Run `bw sync` before reads when stale local vault state could affect the task.
- Lock or log out when finished with direct local work: `bw lock` or
  `bw logout`.
- Never commit exported vault data, `BW_SESSION`, master passwords, API client
  secrets, item JSON containing secret fields, or command transcripts that
  include secret values.

Useful local checks:

```bash
bw --version
bw status
bw list items --search github
bw get item ITEM_ID_OR_NAME
bw sync
```

## Failure Discipline

- If `secure_cli` returns `auth_required`, stop and ask the user to run
  `/auth bitwarden`; do not ask for `BW_SESSION` in chat.
- If `bw` is not installed in the broker/container, report that the broker host
  needs the Bitwarden CLI installed or bundled before retrying.
- If `bw status` says the vault is locked, ask the user to unlock and submit a
  fresh session through `/auth bitwarden`.
- If item lookup by name is ambiguous, use `credential.search` first and then
  reference the chosen `item_id`.
- For any action that uses a secret, summarize the target provider/action and
  selected credential metadata first; never reveal or request the secret value.
