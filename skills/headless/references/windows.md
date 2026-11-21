# Windows Details (Windows 11 and Windows Server 2025)

## Before the Skill Starts (At the PC)

- **Windows 11 (Home or Pro)** or **Windows Server 2025** on `x86_64` or `Arm64`.
- **Local administrator account with a password** (not a Microsoft account: automatic sign-in and OpenSSH require a local password).
  - Account name constraints: up to 20 characters using only letters, digits, dots, dashes, and underscores (no spaces). If the existing admin account has a space, create a dedicated local admin account such as `headless`.
- **OpenSSH Server installed and started** in elevated PowerShell (`Terminal (Admin)`):
  ```powershell
  Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
  Set-Service -Name sshd -StartupType Automatic
  Start-Service sshd
  ```
  If `Add-WindowsCapability` fails, install **OpenSSH Server** via `Settings > System > Optional features > View features`.
- **Firewall profile**: OpenSSH's default rule (`OpenSSH-Server-In-TCP`, port 22) applies only to **Private** networks. If the PC is on a trusted home/office network currently marked Public, switch it to Private:
  ```powershell
  Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private
  ```
  Do not open SSH on untrusted Public networks.
- **Address**: IPv4 address under `Settings > Network & internet > Properties` (or `<hostname>.local`).

## `settings.json` Options

| Setting | Default | Effect |
| --- | --- | --- |
| `user` | (required) | Local admin account for SSH and automatic sign-in. |
| `hostName` | `null` | Computer name (<= 15 letters, digits, dashes); takes effect after restart. |
| `sshKeys` | public key | Written to `C:\ProgramData\ssh\administrators_authorized_keys` (Administrators and SYSTEM ACLs only). |
| `keyOnlySsh` | `true` | Disables SSH password authentication at the top of `C:\ProgramData\ssh\sshd_config` (verified with `sshd -t`; original saved as `sshd_config.before-headless`). |
| `autoLogin` | `true` | Configures Winlogon auto-login using an LSA secret (`DefaultPassword`, never plaintext in the registry; still readable by PC Administrators). Disables Windows-Hello-only restriction if set. Setting `false` removes the secret. |
| `tailscale.enable` | `true` | Installs Tailscale (pinned SHA-256 installer) with `UnattendedMode = always` so it connects before sign-in. Opt out with `--no-tailscale`. |
| `extras.neverSleep` | `true` | Disables hibernation and sleep on mains and battery. |
| `extras.powerButtonShutsDown` | `true` | Sets power button action to clean shutdown. |
| `extras.hideSleep` | `true` | Removes Sleep from Start menu power options. |
| `extras.updatesOvernight` | `true` | Sets Windows Update active hours to 08:00–02:00 so restarts happen overnight. |

Add custom idempotent PowerShell tasks in `machine.ps1` (runs after headless settings on every `apply.sh`).

## On-PC Locations

- `C:\ProgramData\headless\remote`: helper scripts (Administrators and SYSTEM only).
- `C:\ProgramData\headless\config`: copied config folder (excluding `.git`, `known_hosts`, `headless.conf`, and `headless.env`).
- `C:\ProgramData\headless\settings.json`: applied settings record read by `verify.sh`.

## Tailscale Ownership on Windows

Tailscale on Windows answers only the Windows account that joined it:

- If another account already joined it with **Run unattended**, it remains owned by that account and connects at boot.
- If another account joined it without **Run unattended**, `apply.sh` sets unattended policy, the old account signs out on reboot, and `tailscale.sh` joins it as the headless account after restart.
- To transfer ownership immediately (only with explicit user agreement, over the LAN address — never over Tailscale): run `tailscale.sh DIR --uninstall`, then `apply.sh`, then `tailscale.sh`.

## Common Failures

| Error | Cause and Fix |
| --- | --- |
| `does not answer on port 22` | OpenSSH Server not started or network profile is still Public. |
| `password does not work` | Ensure local account password (not Windows Hello PIN) is saved in the credential store. |
| `not an administrator` | Add account to local Administrators group or use another local admin account. |
| `did not sign in by itself` | Domain-joined PCs or legal-notice policies pause at sign-in; check password in store and re-run `apply.sh`. |
| `changed host key` | Confirm whether Windows was reinstalled before removing `known_hosts`. |

## Removal

Set `"autoLogin": false` and run `apply.sh` to delete the LSA secret. Then at the PC remove `C:\ProgramData\headless`, restore `C:\ProgramData\ssh\sshd_config.before-headless`, and optionally uninstall Tailscale and OpenSSH Server in `Settings > Apps`.
