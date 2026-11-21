# Storing All Credentials in the Credential Store

Keep **every** secret used for headless setup and ongoing operations inside a real credential store:

- Remote admin password (`PASSWORD_REF`)
- SSH private key (`SSH_KEY_REF` or secret-store SSH agent via `SSH_AGENT_PUBKEY`)
- SSH key passphrase, if the key is encrypted (`SSH_PASSPHRASE_REF`)
- Tailscale auth key, if joining without an interactive link (`TAILSCALE_KEY_REF`)
- Any remote CLI / provider API keys or bootstrap secrets

The agent never sees a secret value. It records only store entry names in `headless.conf` (or UA catalog metadata keys). `scripts/secret-run.sh` pipes secrets over file descriptors (`3` for admin password, `4` for Tailscale auth key, `5` for SSH private key, `6` for SSH key passphrase).

## 1. Universal Agents Credential Store (Required in UA)

Inside Universal Agents, store **every** secret in the person's UA credential store (`credential_catalog` / Sealbox or broker-owned password manager) using TeamArchitect's `secure_credential_collection_request`. Never store plaintext keys in `.ssh/` or secrets in `.env` files inside workspaces; UA blocks both. See [universal-agents.md](universal-agents.md).

## 2. 1Password (Recommended Cross-Platform + Built-in SSH Agent)

With the [1Password CLI](https://developer.1password.com/docs/cli/) signed in:

- **Admin password**: Save a Password or Login item, reference as `op:op://Private/Headless Box/password`.
- **SSH key (best — 1Password SSH Agent)**: Create or import an Ed25519 SSH Key item in 1Password and enable the 1Password SSH Agent. Export only the **public key** (`ssh-ed25519 ...`) to pass to `--ssh-agent-pubkey`. The private key never touches disk.
- **SSH key (direct vault reference)**: Reference the private key field as `op:op://Private/Headless SSH Key/private key` with `--ssh-key-ref` and pass its non-secret public key via `--ssh-pubkey`.
- **Tailscale auth key**: Save as a concealed field, reference as `op:op://Private/Tailscale/auth-key`.

## 3. Bitwarden (Cross-Platform + Built-in SSH Agent)

With the [Bitwarden CLI](https://bitwarden.com/help/cli/) unlocked (`BW_SESSION` set in a trusted local shell — never in UA `shell`, where raw `bw` is blocked):

- **Admin password**: Save a Login item and reference as `bw:ITEM`.
- **SSH key (best — Bitwarden Desktop SSH Agent)**: Store the SSH key in Bitwarden and enable the Bitwarden SSH Agent; pass only the public key via `--ssh-agent-pubkey`.
- **SSH key (direct CLI reference)**:
  - Native Bitwarden SSH Key item: `bw-ssh:ITEM`
  - Secure Note containing the private key: `bw-notes:ITEM`
  - Custom field (for passphrase or Tailscale auth key): `bw-field:ITEM:FIELD_NAME`

## 4. Automic Vault (Recommended on macOS)

[Automic Vault](https://github.com/automic-vault/automic-vault) stores secrets in the macOS Data Protection Keychain and prompts for approval on each exact command:

```sh
av save HEADLESS_BOX_PASSWORD
av save HEADLESS_BOX_SSH_KEY
av save HEADLESS_BOX_TAILSCALE_KEY
```

Reference entries as `av:HEADLESS_BOX_PASSWORD`, `av:HEADLESS_BOX_SSH_KEY`, and `av:HEADLESS_BOX_TAILSCALE_KEY`. Each run invokes `av inject --mode=fd +NAME:<fd> -- ...` and asks the user to approve.

## 5. Any Other Secret Store (`cmd:`)

Any command that prints only the secret to stdout works with `cmd:COMMAND`:

- **macOS Keychain**:
  ```sh
  security add-generic-password -s headless-box-pw -a admin -w
  ```
  Reference: `cmd:security find-generic-password -s headless-box-pw -w`
- **Linux libsecret (`secret-tool`)**, **`pass`**, **`gopass`**, or **`vault`**: wrap the store's lookup command in `cmd:...`.

## 6. T3 Code Interactive Bootstrap (`request_secret`)

When running inside T3 Code and a one-time secret (such as an initial sudo password) is not yet in a vault:

- Call T3 Code's `request_secret` tool with `delivery: "file"` rather than asking for the secret in chat.
- Pipe the temporary file to the command (`< "$file"`) and instruct the user to save long-lived credentials into their real credential store afterwards.

## 7. Last Resort: Private Env File (Discouraged; Forbidden in UA)

Use only outside Universal Agents when no secret store is available:

```sh
mkdir -p ~/.config/headless && chmod 700 ~/.config/headless
touch ~/.config/headless/box.env && chmod 600 ~/.config/headless/box.env
# In an editor, add: HEADLESS_PASSWORD=the-password
```

Reference: `env:~/.config/headless/box.env:HEADLESS_PASSWORD`. Keep the file **outside** the config folder (`new-config.sh` refuses `env:` files inside the config folder). Warn the user plainly that any process running as their OS account can read a plaintext file; prefer a real credential store with per-use approval or hardware-backed SSH agent.

## 8. Host-Side Auto-Login Password Caveats

- **macOS (`autoLogin: true`)**: macOS stores the boot auto-login password in root-only `/etc/kcpassword` (obfuscated, not strongly encrypted; recoverable by root or anyone with physical disk access while FileVault is off). Setting `"autoLogin": false` removes `/etc/kcpassword`.
- **Windows (`autoLogin: true`)**: Windows stores `DefaultPassword` as an LSA secret (never plaintext in the registry), which an Administrator on the PC can still read back. Setting `"autoLogin": false` removes it.
- **Linux (`autoLogin: true`)**: Enables systemd lingering (`loginctl enable-linger`) so user services start at boot without storing any login password on disk.
