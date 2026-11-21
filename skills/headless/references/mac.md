# Mac Details (Apple Silicon)

## Before the Skill Starts (At the Mac)

- **Apple silicon, current macOS** (Intel Macs are not supported).
- **Administrator account with a password**: the account the skill signs in as and configures for automatic sign-in.
- **Remote Login enabled**: `System Settings > General > Sharing > Remote Login`, allowing that admin account.
- **FileVault**: may stay on initially. When `autoLogin` is `true`, `admin.sh` disables FileVault and waits for decryption so restarts do not pause at the FileVault unlock screen. If the user keeps FileVault on, set `"autoLogin": false` (`--no-auto-login`) and note that after a reboot SSH accepts only the FileVault unlock password until unlocked.
- **Address**: shown under `System Settings > General > Sharing` (for example `mac-mini.local` or LAN IP such as `192.0.2.20`).

## `settings.json` Options

Managed by `modules/darwin/headless.nix` from `github:kunchenguid/headless`:

| Option | Default | Effect |
| --- | --- | --- |
| `user` | (required) | Admin account (`nix-darwin` primary user). Lowercase letter/digit/underscore start, remaining chars may include dashes. |
| `hostName` | `null` | ComputerName, LocalHostName, HostName; `null` preserves current name. |
| `sshKeys` | public key | Public keys allowed to sign in alongside `~/.ssh/authorized_keys`. |
| `keyOnlySsh` | `true` | Disables SSH password, keyboard-interactive, and root login. |
| `autoLogin` | `true` | Signs the admin account in at boot; `false` removes `/etc/kcpassword`. |
| `tailscale.enable` | `true` | Runs the open-source `tailscaled` daemon (set `false` via `--no-tailscale` if `/Applications/Tailscale.app` is already installed). |
| `extras.neverSleep` | `true` | Disables system and disk sleep; display sleeps after 10 minutes. |
| `extras.startAfterPowerLoss` | `true` | Automatically powers on after power loss. |
| `extras.wakeOnLan` | `true` | Enables Wake for network access. |
| `extras.powerNapOff` | `true` | Disables Power Nap. |
| `extras.spotlightOff` | `true` | Disables Spotlight indexing on all volumes. |
| `extras.siriOff` | `true` | Disables Siri for the account. |

Note: Turning an extra off later stops managing it without reverting macOS back to its original default (`autoLogin: false` is the exception and removes `/etc/kcpassword`). Virtual Macs without power-loss or wake-on-LAN settings report `n/a` in `verify.sh`.

Add extra packages, launchd services, or macOS defaults in `machine.nix` and re-run `apply.sh`.

## FileVault Disabling in `admin.sh`

When `autoLogin` is `true` and FileVault is enabled:

1. `admin.sh` installs Determinate Nix first, then runs `fdesetup disable -inputplist` as root via stdin (never on a command line).
2. If FileVault is still encrypting, it waits until encryption completes.
3. If the account lacks a Secure Token or MDM forbids disabling FileVault, `admin.sh` stops with `ask the user:`. Relay that message verbatim; the user either disables FileVault at the Mac or switches `"autoLogin": false`, then re-runs `admin.sh`.
4. Once decryption starts, `admin.sh` waits until `fdesetup status` reports `FileVault is Off`.

## On-Mac Locations

- `~/.headless/config`: copied config folder (without `.git`, `known_hosts`, `headless.conf`, or `headless.env`).
- `~/.headless/remote`: remote helper scripts.
- `/etc/kcpassword`: root-only macOS auto-login credential (present only when `autoLogin` is `true`).
- `/etc/ssh/sshd_config.d/000-headless.conf`: key-only SSH rules (loaded before `100-macos.conf`).
- `/etc/*.before-nix-darwin`: backed-up shell rc files moved aside before first switch.

## Common Failures

| Error | Cause and Fix |
| --- | --- |
| `gave no single ed25519 host key` | Remote Login is off or address is wrong. |
| `shows a different host key than the one pinned` | Machine was reinstalled or another host holds the IP; confirm before removing `known_hosts`. |
| `password sign-in ... failed` | Wrong password in credential store or account not allowed under Remote Login. |
| `is not an administrator` | Use an admin account or grant admin privileges at the Mac. |
| `the Tailscale app is on ...` | `/Applications/Tailscale.app` is installed; set `"tailscale": { "enable": false }` (`--no-tailscale`) and keep using the app. |
| `ask the user: ... FileVault ...` | Disable FileVault manually at the Mac or set `"autoLogin": false`, then re-run `admin.sh`. |
| `did not come back within ... seconds` | Check the screen; if FileVault is still on, macOS is waiting at its unlock screen. |

## Removal

Run `sudo /run/current-system/sw/bin/darwin-uninstaller`, then `/nix/nix-installer uninstall`, restore `/etc/*.before-nix-darwin`, and delete `/etc/ssh/sshd_config.d/000-headless.conf` and `/etc/kcpassword`.
