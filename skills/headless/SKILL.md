---
name: headless
description: Sets up, hardens, verifies, and updates a headless Mac (Apple silicon), Linux (NixOS, Debian, Ubuntu, Fedora), or Windows (11 or Server 2025) machine over SSH with key-only SSH, automatic sign-in or lingering, never-sleep settings, strongly recommended Tailscale, all credentials (admin passwords, SSH keys, passphrases, Tailscale auth keys, and CLI tokens) kept in a credential store, plus full adaptations for Universal Agents (UA credential store and brokered execution boundaries) and T3 Code (full T3 fleet integration with T3 Code, Claude Code, Codex, Antigravity CLIs, and bidirectional environment linking). Use when configuring, bootstrapping, updating, or fleet-integrating a headless remote machine.
license: MIT
---

# Headless Machine Setup and Fleet Integration

Configure one headless Mac, Linux, or Windows machine step by step: explain each step, run it, verify the output, and only then advance. Every step is idempotent and safe to re-run.

All bundled scripts live under this skill's `scripts/` directory; invoke them by path (`$SKILL` below means this skill's folder).

## 1. Detect the Active Runtime Scenario

Identify which environment is running before choosing credential storage and remote execution steps:

| Runtime | Signals | Required Workflow |
| --- | --- | --- |
| **Universal Agents (UA)** | `secure_cli`, `set_up_tools`, `request_access`, `secure_credential_collection_request`, or `list_execution_ssh_targets` tools are present | Load `secure-credential-workflows` and `shell-execution-workflows`. Read [references/universal-agents.md](references/universal-agents.md). Store every secret in the UA credential store and respect UA's broker/sandbox SSH boundaries. |
| **T3 Code** | T3 Code tools (`t3_environment_links`, `t3_environment_link`, `request_secret`, `orchestrator_capabilities`) or `t3` CLI (`T3CODE_HOME` / `T3CODE_THREAD_ID`) are present | Run the baseline headless hardening (with Tailscale strongly recommended), then complete **T3 Fleet Integration** in [references/t3-code-fleet.md](references/t3-code-fleet.md): install `t3`, `claude`, `codex`, `agy`, start the T3 background service, and link local and remote environments bidirectionally. |
| **Standalone / Local Shell** | Neither UA nor T3 Code tools are present | Run the baseline headless procedure below using a real credential store for every secret (passwords, SSH private keys, passphrases, and Tailscale auth keys) and strongly recommend Tailscale. |

## 2. Invariant Rules

- **Never see or print any secret.** Never ask the user to paste passwords, SSH private keys, passphrases, Tailscale auth keys, T3 pairing codes, or API keys in chat. Never run a command that prints a secret (`op read`, `bw get`, `cat` on a key or `.env` file, `echo $...`). Hold only credential-store entry references (or UA `credential_key` metadata).
- **Store ALL credentials in the credential store.** Keep not only the admin password, but also SSH private keys (and any passphrase), Tailscale auth keys, and remote CLI/provider credentials in the credential store. Avoid unencrypted on-disk `~/.ssh/id_*` files and plaintext `.env` files whenever a secret store or secret-store SSH agent is available. See [references/secrets.md](references/secrets.md).
- **Strongly recommend and enable Tailscale by default.** Default `tailscale.enable` to `true` and set up Tailscale unless the user explicitly opts out (`--no-tailscale`) or the machine already runs macOS `/Applications/Tailscale.app`. See [references/tailscale.md](references/tailscale.md).
- **Never weaken sudo.** Do not add passwordless `sudo` rules. Every privileged step reads the admin password from the store and pipes it to `sudo -S`.
- **Key before key-only.** Disable SSH password authentication only after `connect.sh` proves key authentication works against the pinned host key.
- **Ask before destructive or unchosen changes.** Confirm disk wipes (`nixos-anywhere`), restarts, Tailscale uninstall/takeover on Windows, and T3 environment access levels before proceeding.

## 3. Scenario 1: Universal Agents

When running in Universal Agents, read [references/universal-agents.md](references/universal-agents.md) before touching credentials or shell commands.

1. **Store every credential in the UA credential store (Sealbox / `credential_catalog`)**:
   - Inspect existing metadata first with `secure_cli(provider="credential_catalog", action="credential.get_metadata", ...)` or `secure_cli(provider="sealbox", action="credential.search", ...)`.
   - Collect missing credentials (admin password, SSH private key + optional passphrase, Tailscale auth key, CLI tokens) through TeamArchitect's `secure_credential_collection_request` form (specialists escalate with `manager_escalation`, `escalation_type="needs_user_input"`).
   - Never invoke `bw`, `op`, `vault`, `keepass`, or `secret-run.sh` with `ua:` in UA `shell`; UA blocks password-manager CLIs and sensitive paths (`.ssh`, `id_ed25519`, `*.key`, `*.pem`, `*.env`).
   - Keep generated non-secret machine config in `headless.conf` (never `*.env`) and `settings.json` inside the task's workspace folder.
2. **Choose the verified UA SSH execution path**:
   - **Why raw SSH from UA `shell` cannot bootstrap with Sealbox secrets**: UA's Landlock/OpenShell sandbox gives each command an ephemeral `HOME`/`TMPDIR`, blocks `.ssh`/key/`.env` paths, strips secret env vars, and never exposes Sealbox secrets to agent shell. `secure_cli` has no built-in `ssh` provider.
   - **Path A — Ongoing management via UA's brokered SSH (`fn:execution_control`)**: Use `list_execution_ssh_targets` → `create_execution_ssh_session` → `open_execution_ssh_session` → `plan_execution_ssh_interaction` + `apply_change` → `write_execution_ssh_session` / `read_execution_ssh_session` → `close_execution_ssh_session`. Requires an operator-pinned target in `instance_config.yaml` (`execution_control.ssh.targets`) with host-side key and `known_hosts` files outside `workspaces/`; cannot bootstrap a password-only machine or inject Sealbox sudo passwords.
   - **Path B — Administrator-approved Installed CLI (`cli:<name>` via `propose_access_change`)**: For repeatable short brokered SSH operations (< 120 seconds, `RUN_TIMEOUT_SECONDS = 120`), propose a SHA-256-pinned single-file runner in `team/tools/` with `InjectionPlacement.FILE` (`0600` in the broker's ephemeral run dir) and `InjectionPlacement.ENV` linked to the user's UA credential record. Long steps (Nix install, FileVault decryption, `nixos-anywhere`) exceed 120 seconds and must be split into start/poll steps or handed off.
   - **Path C — Guided handoff (default when neither Path A nor Path B is configured)**: Keep all secrets in the UA credential store, generate the non-secret config bundle (`settings.json`, `headless.conf`, platform templates) in the person's folder, explain the exact broker boundary clearly, and hand the user the exact local or T3 Code commands to execute.

## 4. Scenario 2: T3 Code Fleet Integration

When running in T3 Code, complete the baseline headless OS hardening (Section 5–7 below, with Tailscale enabled), then prepare the remote machine for full T3 fleet integration. Read [references/t3-code-fleet.md](references/t3-code-fleet.md) for full details and recovery steps.

1. **Collect any needed bootstrap secret safely**: Use the credential store for all persistent secrets (admin password, SSH key, Tailscale auth key, CLI API keys). If a one-time user secret (such as a sudo password not yet in a vault) is required interactively, call `request_secret` with `delivery: "file"` rather than asking in chat.
2. **Confirm fleet selections with the user** (defaults in **bold**):
   - Agent CLIs to install on the remote machine: **`t3`**, **`claude`**, **`codex`**, **`agy`** (all on by default; user may deselect any).
   - Remote T3 transport: **Tailscale Serve HTTPS** (preferred when Tailscale is set up), **T3 Connect** (`t3 up --connect --headless`), or LAN fallback.
   - Bidirectional linking access level: **`approval-required`** (choices: `read-only`, `approval-required`, `auto-accept-edits`, `auto`, `full-access`).
3. **Install T3 Code and coding-agent CLIs on the remote machine**:
   ```sh
   $SKILL/scripts/t3/install-fleet.sh ~/headless/<name> \
     --platform mac|linux|windows \
     --clis t3,claude,codex,agy \
     --transport tailscale [--protect-service]
   ```
   Guide the user to sign in to each installed provider CLI (`claude`, `codex`, `agy`) on the remote machine (device flow or stored credentials; never paste tokens in chat).
4. **Link the machines bidirectionally (add each to the other's environment)**:
   - Check existing links first via `t3_environment_links` (or `t3 environment list --json`). Remind the user to enable **Settings → Labs → Linked environments** if link tools are absent.
   - **Option A — Automated bidirectional pipe (no pairing code printed)**:
     ```sh
     $SKILL/scripts/t3/link-fleet.sh ~/headless/<name> \
       --platform mac|linux|windows \
       --direction both \
       --access approval-required \
       --transport tailscale
     ```
   - **Option B — Interactive T3 Code link card**: Call `t3_environment_link` with `url` (the remote Tailscale Serve HTTPS or T3 Connect address), `hint`, `reason`, and `requestedAccess` to link remote into local; then run `link-fleet.sh --direction local-to-remote` (or link local from the remote T3 UI) so both machines can orchestrate each other. Never paste pairing codes in chat.
5. **Verify fleet readiness and reboot survival**:
   ```sh
   $SKILL/scripts/t3/verify-fleet.sh ~/headless/<name> \
     --platform mac|linux|windows --clis t3,claude,codex,agy
   ```
   Confirm `t3_environment_links` reports the remote environment answering, call `orchestrator_capabilities(environmentId="<remote-id>")` to confirm remote providers/models are visible, restart the remote machine (`restart.sh`), and verify both Tailscale and `t3_environment_links` recover automatically.

## 5. Baseline Setup: Shared Credential & Config Steps (All Platforms)

### Step A: Prepare the Machine (User Action)

- **Mac (Apple silicon)**: Confirm an admin account with password, Remote Login on (`System Settings > General > Sharing > Remote Login`), and address (IP or `name.local`). FileVault may stay on (Step M5 disables it if automatic sign-in is chosen). See [references/mac.md](references/mac.md).
- **Linux (systemd: NixOS, Debian, Ubuntu, Fedora)**: Confirm reachable SSH server, non-root account with password in `sudo` or `wheel`, and address. See [references/linux.md](references/linux.md).
- **Windows (11 or Server 2025)**: Confirm a local administrator account (no spaces, <= 20 chars, not a Microsoft account), address, and run in elevated PowerShell:
  ```powershell
  Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
  Set-Service -Name sshd -StartupType Automatic
  Start-Service sshd
  # If on a trusted home/office network currently marked Public:
  Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private
  ```
  See [references/windows.md](references/windows.md).

### Step B: Store All Credentials in the Credential Store (User Action)

Have the user store **every** secret in their credential store before creating the config folder (see [references/secrets.md](references/secrets.md) for exact commands per store):

1. **Admin password** (`--password-ref`): `av:NAME`, `op:op://Vault/Item/password`, `bw:ITEM`, `cmd:COMMAND`, or (UA) `credential_catalog` / Sealbox.
2. **SSH key** (choose one credential-store method):
   - **Secret-store SSH agent (preferred)**: Keep the Ed25519 key in 1Password SSH Agent, Bitwarden SSH Agent, or macOS Keychain; pass `--ssh-agent-pubkey <pubkey-file-or-line>`. No private key ever touches disk.
   - **Secret-store key reference**: Store the private key in the vault (`op:op://Vault/SSH/private key`, `bw-ssh:ITEM`, `bw-notes:ITEM`, `av:HEADLESS_SSH_KEY`) plus optional `--ssh-passphrase-ref`, and pass `--ssh-key-ref ENTRY --ssh-pubkey <pubkey-file-or-line>`. `lib.sh` materializes it transiently in a `0700` `/dev/shm` or temp directory with mode `0600` and removes it on exit.
3. **Tailscale auth key (optional)** (`--tailscale-key-ref`): Store a reusable/ephemeral Tailscale auth key in the same store for zero-click join; otherwise `tailscale.sh` prints a browser approval link.

### Step C: Create the Config Folder

Ask the user's choices (defaults in **bold**):

- Config folder path: **`~/headless/<machine-name>`** (git-tracked, never holds secrets).
- Host name: **keep current**, or set a new one (Windows <= 15 chars).
- Automatic sign-in / lingering: **on** (on macOS, warn that turning FileVault off leaves the disk unencrypted at rest and `/etc/kcpassword` is root-recoverable; on Windows, LSA secret is administrator-recoverable).
- **Tailscale: ON (strongly recommended)**. Explain that Tailscale provides port-free off-LAN access, stable addresses, and private HTTPS (`t3 pair --tailscale`) for T3 fleets. Only pass `--no-tailscale` if the user explicitly declines or macOS already runs `/Applications/Tailscale.app`.
- Platform extras (all **on** by default; turn any off with `--extra-off NAME`):
  - Mac: `neverSleep`, `startAfterPowerLoss`, `wakeOnLan`, `powerNapOff`, `spotlightOff`, `siriOff`
  - Linux: `neverSleep`, `autoUpdates`
  - Windows: `neverSleep`, `powerButtonShutsDown`, `hideSleep`, `updatesOvernight`

Create the config folder (replace `<platform>` with `mac`, `linux`, or `windows`):

```sh
$SKILL/scripts/<platform>/new-config.sh ~/headless/<name> \
  --address ADDRESS --login ACCOUNT --password-ref ENTRY \
  --ssh-agent-pubkey ~/.ssh/id_ed25519.pub \
  [--host-name NAME] [--no-auto-login] \
  [--no-tailscale] [--tailscale-key-ref ENTRY] [--extra-off NAME]...
```

*(When using a vault-stored private key instead of a secret-store SSH agent, replace `--ssh-agent-pubkey ...` with `--ssh-key-ref ENTRY --ssh-pubkey <pubkey-file-or-line> [--ssh-passphrase-ref ENTRY]`.)*

This writes `settings.json`, `headless.conf` (containing only store references, no secrets), `authorized_key.pub`, and platform templates. Show `settings.json` to the user before continuing.

## 6. Platform Execution Sequences

### Mac (Apple silicon)

1. **First sign-in**: `$SKILL/scripts/mac/connect.sh ~/headless/<name>` — pins ed25519 host key, prints fingerprint for user verification, installs public key, verifies key login.
2. **Admin session**: `$SKILL/scripts/mac/admin.sh ~/headless/<name>` — installs Determinate Nix, writes `/etc/kcpassword` if `autoLogin` is on, disables FileVault and waits for decryption when needed. Pass on any `ask the user:` line verbatim.
3. **Apply config**: `$SKILL/scripts/mac/apply.sh ~/headless/<name>` — builds and switches `nix-darwin`, copies `flake.lock` back. Commit the config folder afterward.
4. **Join Tailscale (strongly recommended)**: `$SKILL/scripts/mac/tailscale.sh ~/headless/<name>` (and `--wait` if using a sign-in link). Offer to update `ADDRESS` in `headless.conf` to the Tailscale IP/MagicDNS name and re-pin `known_hosts`.
5. **Verify, restart, verify**:
   ```sh
   $SKILL/scripts/mac/verify.sh ~/headless/<name>
   $SKILL/scripts/mac/restart.sh ~/headless/<name>
   $SKILL/scripts/mac/verify.sh ~/headless/<name>
   ```
   Tell the user before restarting. If running in T3 Code, proceed to Section 4.

### Linux (NixOS, Debian, Ubuntu, Fedora)

1. **First sign-in**: `$SKILL/scripts/linux/connect.sh ~/headless/<name>` — pins host key, installs public key, reports detected distribution.
2. **Optional NixOS replacement** (non-NixOS only): Offer `nixos-anywhere` only after warning plainly that it **erases the entire disk** (requires Nix locally, x86_64/aarch64, 2 GB RAM, Secure Boot off, wired IPv4):
   ```sh
   $SKILL/scripts/linux/install-nixos.sh ~/headless/<name> --list-disks
   $SKILL/scripts/linux/install-nixos.sh ~/headless/<name> --disk /dev/DISK --yes-wipe
   ```
   Never pass `--yes-wipe` until the user explicitly names and approves the disk.
3. **Apply config**: `$SKILL/scripts/linux/apply.sh ~/headless/<name>` (on existing NixOS, passes `--nixos-branch` if prompted; warn user to check copied `nixos/` before pushing to git). Commit the config folder afterward.
4. **Join Tailscale (strongly recommended)**: `$SKILL/scripts/linux/tailscale.sh ~/headless/<name>` (and `--wait` if using a sign-in link). Offer to switch `ADDRESS` to the Tailscale IP/MagicDNS name.
5. **Verify, restart, verify**:
   ```sh
   $SKILL/scripts/linux/verify.sh ~/headless/<name>
   $SKILL/scripts/linux/restart.sh ~/headless/<name>
   $SKILL/scripts/linux/verify.sh ~/headless/<name>
   ```
   Tell the user before restarting. If running in T3 Code, proceed to Section 4.

### Windows (11 or Server 2025)

1. **First sign-in**: `$SKILL/scripts/windows/connect.sh ~/headless/<name>` — pins host key, adds key to `C:\ProgramData\ssh\administrators_authorized_keys` with strict ACLs.
2. **Apply config**: `$SKILL/scripts/windows/apply.sh ~/headless/<name>` — applies key-only SSH, power/update settings, LSA secret auto-login (if enabled), and unattended Tailscale install/policy. Commit the config folder afterward.
3. **Join Tailscale (strongly recommended)**: `$SKILL/scripts/windows/tailscale.sh ~/headless/<name>` (and `--wait` if using a sign-in link). Respect existing Windows-account Tailscale ownership; ask before running `--uninstall`.
4. **Verify, restart, verify**:
   ```sh
   $SKILL/scripts/windows/verify.sh ~/headless/<name>
   $SKILL/scripts/windows/restart.sh ~/headless/<name>
   $SKILL/scripts/windows/verify.sh ~/headless/<name>
   ```
   Tell the user before restarting. If running in T3 Code, proceed to Section 4.

## 7. Updates and Failure Recovery

- **Ongoing updates**: Edit `settings.json`, `machine.nix`, or `machine.ps1`, then re-run `apply.sh` and `verify.sh`.
- **Changed host key**: Every script stops on a host-key mismatch. Ask the user whether the machine was reinstalled before removing `known_hosts`.
- **Failed step**: Read the last `headless:` error line and consult the matching platform reference (`references/mac.md`, `references/linux.md`, `references/windows.md`, `references/t3-code-fleet.md`, or `references/universal-agents.md`). Never bypass failures by re-enabling password SSH, adding passwordless sudo, or printing secrets.

## 8. Completion Evidence

Confirm before finishing:

- Key-only SSH verified and password login refused (`verify.sh` passes after a full restart).
- All credentials (admin password, SSH private key/passphrase, Tailscale auth key, CLI tokens) reside in the credential store and zero secrets appear in git, logs, or chat.
- Tailscale connected (or explicit user opt-out / existing `Tailscale.app` noted).
- In Universal Agents: credentials stored in UA credential store and broker/SSH execution status verified or cleanly handed off.
- In T3 Code: `t3`, requested CLIs (`claude`, `codex`, `agy`), background service, and bidirectional T3 environment links verified both before and after restart.
