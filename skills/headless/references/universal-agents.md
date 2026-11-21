# Universal Agents Integration and Broker Reachability

When running inside Universal Agents (UA), load both `secure-credential-workflows` and `shell-execution-workflows` before executing credential or command steps.

## 1. Storing All Credentials in the UA Credential Store

Store **every** credential for the headless machine inside the requesting person's UA credential store (`credential_catalog` backed by Sealbox by default, or broker-owned Bitwarden/1Password/KeePass/Vault via `secure_cli`):

| Credential | Recommended Catalog Key | Field Structure (`secure_credential_collection_request`) |
| --- | --- | --- |
| Remote admin login & password | `headless_<machine>_admin` | `username` (`visibility="metadata_visible"`) + `admin_password` (`kind="password"`, `visibility="secret"`, `input_control="password"`) |
| SSH keypair & optional passphrase | `headless_<machine>_ssh` | `ssh_public_key` (`kind="custom"`, `visibility="metadata_visible"`, `input_control="text"`), `ssh_private_key` (`kind="credential_file"`, `visibility="secret"`, `input_control="file"` or `"textarea"`), optional `ssh_passphrase` (`kind="password"`, `visibility="secret"`, `required=false`) |
| Tailscale auth key (optional) | `headless_<machine>_tailscale` | `tailscale_auth_key` (`kind="token"`, `visibility="secret"`, `input_control="password"`) |
| Combined single-record option (for `cli:headless` Installed CLI) | `headless_<machine>_bundle` | Single catalog record containing `admin_password`, `ssh_private_key`, optional `ssh_passphrase`, and optional `tailscale_auth_key` so one account link injects all fields |
| Remote coding-CLI API keys (if used) | `headless_<machine>_<provider>_key` | `api_token` (`kind="token"`, `visibility="secret"`, `input_control="password"`) |

### Collection Procedure

1. Check existing metadata first with `secure_cli`:
   ```json
   {
     "provider": "credential_catalog",
     "action": "credential.get_metadata",
     "params": {"credential_key": "headless_box_admin"},
     "reason": "Check whether the remote admin credential is already stored."
   }
   ```
   Or search broad username/password records with `provider="sealbox"`, `action="credential.search"`. Never treat `sealbox.credential.search` alone as proof that a custom secret or file credential is missing.
2. For any missing credential, **never** ask the person to paste secrets in chat or upload private keys through chat attachments (UA's `access_control/sensitive_paths.py` refuses `.ssh`, `id_ed25519`, `id_rsa`, `*.key`, `*.pem`, and `*.env` uploads and file paths).
3. TeamArchitect returns a terminal `secure_credential_collection_request` structured action so the gateway opens a broker-hosted secure form. Specialists escalate to TeamArchitect with `manager_escalation` (`escalation_type="needs_user_input"`).
4. Never write `.env` files (such as `headless.env`) inside UA workspaces. UA's `sensitive_paths.py` rejects any path ending in `.env` or starting with `.env.`. Use `headless.conf` and `settings.json` for non-secret configuration.

## 2. Verified UA Broker & Sandbox Boundaries for SSH

Universal Agents intentionally isolates agent `shell` from credentials and secret stores. Verify these exact runtime boundaries before attempting remote commands:

1. **No built-in `ssh` provider in `secure_cli`**: UA's broker catalog (`ua_definitions/access/tools/broker.yaml`) provides `cli:github`, `cli:google`, `cli:x`, `cli:huggingface`, password-manager metadata/action providers (`bitwarden`, `onepassword`, `keepass`, `vault`, `sealbox`), `credential_catalog`, and `secure_requests` (`http:*`). It has no built-in `ssh` or `headless` provider.
2. **External secret-store CLIs and key/env files are blocked in `shell`**:
   - `custom_tools/non_interactive_shell.py` (`BLOCKED_CREDENTIAL_COMMANDS`) blocks `bw`, `op`, `vault`, `keepass`, `keepassxc`, `keepassxc-cli`, `gh`, and `gog` before execution (including nested `sh -c`/`bash -c`).
   - `access_control/sensitive_paths.py` blocks `.ssh`, `id_ed25519`, `id_rsa`, `id_ecdsa`, `id_dsa`, `*.key`, `*.pem`, `*.p12`, `*.pfx`, and `*.env` across file tools and shell command arguments.
   - `custom_tools/code_sandbox.py` (Landlock) gives every `shell` command an ephemeral `HOME`/`TMPDIR` deleted after the command exits, strips secret-like env vars, runs without a PTY/stdin, and prevents reading host credential stores or broker files.
   - `ssh` itself is only blocked for loopback targets (`LOOPBACK_NETWORK_COMMANDS`), not remote hosts, when `fn:internet` is allowed — **however**, an agent in `shell` cannot access private SSH keys or passwords stored in Sealbox without an operator-configured broker bridge.
3. **UA's built-in `execution_control` SSH broker (`fn:execution_control`) has strict preconditions**:
   - Disabled by default (`execution_control.ssh.enabled: false`).
   - Targets must be pre-configured by an operator in `instance_config.yaml` (`execution_control.ssh.targets`) with pinned `host`, `port`, `username`, `host_key_algorithm`, `host_key_fingerprint`, and host-side `identity_file` and `known_hosts_file` paths outside `workspaces/` (`ConfiguredSSHCredentialMaterialProvider`).
   - It does **not** currently read keys or sudo passwords from Sealbox/`credential_catalog`.
   - It hardcodes `BatchMode=yes`, `IdentitiesOnly=yes`, `IdentityAgent=none`, and `StrictHostKeyChecking=yes`: it can only connect to an already-enrolled, key-authenticated host, not bootstrap a fresh password-only machine.
   - Typing into a live PTY requires per-session Inbox approval (`plan_execution_ssh_interaction` + `apply_change`), and the agent still cannot read the admin password from Sealbox to satisfy `sudo -S`.
4. **OpenShell leases (`credential.bind_for_openshell`)**:
   - Available only when `SECURITY_LAYER_MODE=openshell`, requires full access to an operator-defined `linked_credential` tool with `ENV` injections, and injects environment variables only (not `0600` key files), subject to OpenShell's network policy.

## 3. Supported UA Execution Paths

Choose the first path that the current UA instance supports; report the exact capability gap clearly if none of Paths A or B are configured.

### Path A: Ongoing Management via UA Brokered SSH (`fn:execution_control`)

Use after the machine is already bootstrapped for key-only SSH and an operator has pinned it in `instance_config.yaml` (`execution_control.ssh.targets`):

1. Call `list_execution_ssh_targets`. Never substitute a model-authored host, username, key path, or fingerprint for an installed target.
2. Call `create_execution_ssh_session(target_id=...)` and `open_execution_ssh_session(session_id=...)`.
3. Read or resize immediately with `read_execution_ssh_session` / `resize_execution_ssh_session`.
4. Before sending commands, call `plan_execution_ssh_interaction(session_id=..., reason=...)` and `apply_change` so the person approves typing into that exact session in the Inbox.
5. Run non-secret verification or user-level commands via `write_execution_ssh_session` and read bounded output with `read_execution_ssh_session`. Do not prompt for or type raw passwords.
6. Always call `close_execution_ssh_session(session_id=...)` when finished so the bounded transcript artifact is persisted.

### Path B: Administrator-Approved Installed CLI (`cli:<name>`) Backed by UA Credential Store

UA's installed CLI runner (`secure_tool_broker/installed_clis.py`) executes a single administrator-approved, SHA-256-pinned executable from `team/tools/<name>/<file>` inside a required Landlock sandbox (`network=True`) and injects the linked UA credential record via **both** `InjectionPlacement.FILE` (`0600` files in the broker's private ephemeral `run_dir`) and `InjectionPlacement.ENV`, redacting secret values from stdout/stderr and deleting `run_dir` immediately afterward.

- **Works well for**: Short brokered SSH actions (key installation, verification, Tailscale status/join, config check, single-command updates) using credentials stored exclusively in the UA credential store (`headless_<machine>_bundle`).
- **Hard runtime limits to account for**:
  - `RUN_TIMEOUT_SECONDS = 120`: commands longer than 2 minutes time out. Long operations (Determinate Nix install, FileVault decryption, `nixos-anywhere`, large rebuilds) must be split into asynchronous start + status-poll subcommands or run outside UA.
  - `task_roots=()`: the installed CLI sees only its ephemeral `run_dir`, not the agent's workspace folder. Pass non-secret config payloads (such as `settings.json` or a tar stream) via `params.stdin` (up to `MAX_STDIN_CHARS = 1_000_000`).
  - Requires an administrator to approve the `cli:<name>` tool proposal (`propose_access_change`) and link the person's credential record (`/link cli:<name>`).

### Path C: Guided Credential-Safe Handoff (Out-of-the-Box UA)

When neither `execution_control.ssh` nor an approved `cli:headless` / `cli:ssh` installed CLI is configured:

1. Collect and store all remote credentials in the UA credential store so nothing is lost or sent in chat.
2. Generate the non-secret config folder in the person's workspace (`settings.json`, `headless.conf`, and platform templates — never `*.env` or private keys).
3. Explain concretely what did not happen (the UA broker cannot invoke raw SSH with Sealbox credentials directly from agent `shell`), why (UA's shell/sandbox boundary keeps credentials broker-only and has no built-in `ssh` broker provider), and provide the exact next step:
   - Run the generated setup bundle on a local workstation or linked T3 Code environment with direct SSH access, **or**
   - Ask an operator/administrator to enable Path A (`execution_control.ssh.targets`) or approve Path B (`cli:headless` installed CLI).

## 4. UA Platform Enhancements Needed for Seamless Native Headless SSH

If an operator asks what changes in Universal Agents itself would make full headless bootstrap native without Path B workarounds:

1. Wire `SSHSessionBroker` (or a first-class `secure_cli` `ssh` provider) to read SSH private keys, passphrases, and `sudo -S` / first-login passwords directly from `credential_catalog` / Sealbox instead of operator disk files.
2. Add an Inbox host-key pinning / TOFU approval card so newly provisioned hosts can be enrolled without editing `instance_config.yaml`.
3. Support configurable per-tool timeouts (> 120 seconds) or async job progress for long-running installed CLI / brokered SSH operations.
