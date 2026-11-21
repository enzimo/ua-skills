# T3 Code Fleet Integration

When running inside T3 Code, treat a headless remote machine as a **first-class T3 Code Linked Environment**, not merely an SSH box. Complete the baseline OS hardening first (key-only SSH, never-sleep, automatic sign-in or systemd lingering, and **Tailscale strongly recommended**), then prepare the machine for full bidirectional T3 fleet integration.

## 1. Prerequisites and Secret Discipline in T3 Code

- Store all persistent credentials (remote admin password, SSH private key/passphrase, Tailscale auth key, provider API keys) in the user's credential store (`references/secrets.md`).
- If a one-time secret is required interactively (for example a sudo password not yet saved in a vault), call T3 Code's `request_secret` tool (`delivery: "file"` when piping to a command) rather than asking for it in chat.
- Never paste or print T3 pairing codes (`t3 pair` tokens) in chat or terminal logs. Use either the T3 Code `t3_environment_link` card or `scripts/t3/link-fleet.sh` (which pipes `<url> <pairing-code>` directly into `t3 environment link --from -` without echoing).
- Verify that **Settings → Labs → Linked environments** is enabled if `t3_environment_links` / `t3_environment_link` tools are unavailable.

## 2. Confirm Fleet Choices with the User

Confirm these options before installing (defaults in **bold**):

- **CLIs to install on the remote machine**: **`t3`**, **`claude`** (Claude Code), **`codex`** (OpenAI Codex), **`agy`** (Google Antigravity CLI). All four are recommended so the remote machine can run any supported T3 Code provider.
- **Remote T3 transport**:
  1. **Tailscale Serve HTTPS** (strongly recommended when Tailscale is connected): private tailnet HTTPS with zero exposed LAN/public ports, paired via `t3 pair --tailscale`.
  2. **T3 Connect** (`t3 up --connect --headless`): works anywhere through T3 Connect with your T3 account (also enables mobile/desktop relay access).
  3. **LAN** (`t3 up --lan --yes`): fallback when neither Tailscale nor T3 Connect is available; warn plainly that anyone on the local network can reach the port and a pairing code is the only lock.
- **Bidirectional access level** (`--access`): **`approval-required`** by default. Choices: `read-only`, `approval-required`, `auto-accept-edits`, `auto`, `full-access`. Confirm whether both directions should use the same level or different levels.
- **Linux OOM protection (`--protect-service`)**: on Linux with systemd, `t3 service protect` protects the T3 Code server from agents under memory pressure (uses sudo via the credential store).

## 3. Official CLI Install Commands (Reference)

`scripts/t3/install-fleet.sh` runs these idempotently over SSH:

| CLI | macOS / Linux | Windows (PowerShell) | Notes |
| --- | --- | --- | --- |
| **T3 Code (`t3`)** | `curl -fsSL https://t3.codes/install.sh \| sh` | `irm https://t3.codes/install.ps1 \| iex` | Alternative: `npm install -g t3@latest` |
| **Claude Code (`claude`)** | `curl -fsSL https://claude.ai/install.sh \| bash` | `irm https://claude.ai/install.ps1 \| iex` | Alternative: `npm install -g @anthropic-ai/claude-code` |
| **OpenAI Codex (`codex`)** | `curl -fsSL https://chatgpt.com/codex/install.sh \| sh` | `irm https://chatgpt.com/codex/install.ps1 \| iex` | Alternative: `npm install -g @openai/codex` |
| **Antigravity (`agy`)** | `curl -fsSL https://antigravity.google/cli/install.sh \| bash` | `irm https://antigravity.google/cli/install.ps1 \| iex` | Do **not** install unrelated npm `antigravity` or `antigravity-cli` packages. |

Ensure `$HOME/.local/bin` (and `/opt/homebrew/bin` on Apple silicon Macs) is on `PATH` for both login and non-interactive shells so the T3 background service discovers every installed CLI.

## 4. Step-by-Step Fleet Setup

### Step T1: Install CLIs and Start the T3 Background Service

```sh
$SKILL/scripts/t3/install-fleet.sh ~/headless/<name> \
  --platform mac|linux|windows \
  --clis t3,claude,codex,agy \
  --transport tailscale [--protect-service]
```

- With `--transport connect`, `t3 up --connect --headless` prints a device sign-in URL and code; show it to the user to authorize on any device.
- Confirm every CLI prints its version (`ok    t3: ...`, `ok    claude: ...`, `ok    codex: ...`, `ok    agy: ...`).

### Step T2: Authenticate Provider CLIs on the Remote Machine

Each installed provider CLI needs authentication on the remote machine before T3 Code can run turns with it there:

- Prefer interactive device / browser sign-in (`claude`, `codex login`, `agy`) performed by the user over an SSH terminal or via credential-store-backed API keys.
- Never paste API keys or OAuth tokens into chat. If using T3 Code's `request_secret` (`delivery: "file"`) to hydrate a provider key securely, pipe directly into the remote provider's credential store and delete the temporary file immediately.

### Step T3: Link Local and Remote T3 Environments Bidirectionally

Check current links first:
- Inside a T3 Code agent turn: call `t3_environment_links`.
- In shell: run `t3 environment list --json`.

Then add **each machine to the other's environment**:

#### Option A: Automated Bidirectional Pipe (Recommended over SSH)

```sh
$SKILL/scripts/t3/link-fleet.sh ~/headless/<name> \
  --platform mac|linux|windows \
  --direction both \
  --access approval-required \
  --transport tailscale
```

What this does safely:
1. **Remote → Local**: runs `t3 pair --tailscale --ttl 5m --label <local-host>` on the remote, extracts `<url> <pairing-code>` strictly in memory (never echoed), and pipes it to local `t3 environment link --from - --access <level>`.
2. **Local → Remote**: runs `t3 pair --tailscale --ttl 5m --label <remote-host>` locally, extracts `<url> <pairing-code>` strictly in memory, and pipes it over SSH to remote `t3 environment link --from - --access <level>`.

Both linked peers appear in each other's **Settings → Sharing & access → Authorized clients** (where either side can revoke access at any time).

#### Option B: Interactive T3 Code Link Card (When Pairing Manually)

- To link the remote into this T3 Code environment from an agent turn, call `t3_environment_link` with:
  - `url`: the remote's Tailscale Serve HTTPS or T3 Connect address (never guess an address; read it from `t3 status --json` on the remote)
  - `hint`: the remote machine's short name
  - `reason`: one sentence explaining the fleet link
  - `requestedAccess`: chosen access level (default `approval-required`)
  The user completes the pairing in the card; do not wait or poll, and never ask for a pairing code in chat.
- Repeat in the reverse direction so the remote machine also has this machine linked (`link-fleet.sh --direction local-to-remote` or via the remote T3 UI).

### Step T4: Verify Full Fleet Integration and Reboot Survival

1. Run the fleet verifier:
   ```sh
   $SKILL/scripts/t3/verify-fleet.sh ~/headless/<name> \
     --platform mac|linux|windows --clis t3,claude,codex,agy
   ```
2. From the T3 Code agent turn, verify through T3 MCP tools:
   - Call `t3_environment_links` and confirm the remote machine answers.
   - Call `orchestrator_capabilities(environmentId="<remote-environment-id>")` and confirm the installed providers (`claude`, `codex`, `antigravity` / `agy`) and models are reported.
   - Optionally call `t3_environment_read(environmentId="<remote-environment-id>")` to confirm remote server identity and preferences.
3. Restart the remote machine (`$SKILL/scripts/<platform>/restart.sh ~/headless/<name>` — tell the user first), then re-run `verify-fleet.sh` and `t3_environment_links` to prove that Tailscale, the T3 background service, and bidirectional links survive a cold reboot.

## 5. Troubleshooting T3 Fleet Issues

- **Remote `t3 pair --tailscale` fails**: Confirm Tailscale is connected (`tailscale status`), Tailscale Serve is enabled on the tailnet, and `t3 status --json` shows the T3 service running. If Tailscale Serve is disabled in the tailnet admin console, enable HTTPS / Serve there or fall back to `--transport connect`.
- **Local `t3 pair --tailscale` fails during `local-to-remote`**: Verify the local machine is also running a T3 Code server reachable over Tailscale Serve or T3 Connect (`t3 status --json`). Pass `--local-url` if the local server uses an explicit reachable address.
- **Provider CLI installed but not listed by `orchestrator_capabilities`**: Confirm the CLI is on the background service's `PATH` (not just an interactive shell alias), restart the T3 service (`t3 service restart`), and verify provider authentication on the remote machine.
- **Expired or revoked link**: Re-run `link-fleet.sh` (or call `t3_environment_link`) after confirming `t3 status --json` on both machines.
