# Linux Details (NixOS, Debian, Ubuntu, Fedora)

## Before the Skill Starts (At the Machine)

- **systemd** on `x86_64` or `aarch64`. NixOS uses `headless.nixosModules.headless`; Debian, Ubuntu, and Fedora (`dnf5`) use the distro-neutral script.
- **Non-root account with a password and `sudo` access** (member of `sudo` on Debian/Ubuntu or `wheel` on Fedora/NixOS). Root login is never used and passwordless sudo is never added.
- **Reachable SSH server** allowing password login for the initial `connect.sh` key enrollment.
- **Address**: LAN IP (for example `192.0.2.20`) or reachable hostname.

## `settings.json` Options

| Setting | Default | Effect |
| --- | --- | --- |
| `user` | (required) | Admin account name. |
| `hostName` | `null` | Machine hostname; `null` keeps current. |
| `sshKeys` | public key | Public keys allowed to sign in alongside `~/.ssh/authorized_keys`. |
| `keyOnlySsh` | `true` | Disables SSH password, keyboard-interactive, and root sign-in (`/etc/ssh/sshd_config.d/00-headless.conf`). |
| `autoLogin` | `true` | Enables systemd lingering (`loginctl enable-linger`) so user services (including `t3` background service) start at boot without interactive login. |
| `tailscale.enable` | `true` | Installs and enables `tailscaled` (NixOS module or Tailscale's signed package repository). Opt out with `--no-tailscale`. |
| `extras.neverSleep` | `true` | Masks `sleep.target`, `suspend.target`, `hibernate.target`, and `hybrid-sleep.target`. |
| `extras.autoUpdates` | `true` | Distro script: enables `unattended-upgrades` (apt) or `dnf5-automatic`. NixOS: updates come from the config folder or `system.autoUpgrade`. |

## Existing NixOS Machines

- The first `apply.sh` copies `/etc/nixos` into `nixos/` inside the config folder and writes `system.nix` importing it. Inspect `nixos/` for private data before pushing the config folder to a git remote.
- `apply.sh` follows the NixOS release branch read from root's `nixos` channel (for example `nixos-26.05` or `nixos-unstable`). If it cannot match the branch automatically, pass `--nixos-branch <branch>`.
- After switching, `apply.sh` installs the folder into `/etc/nixos` (preserving the prior directory at `/etc/nixos.before-headless`).
- If `/etc/nixos` is already a flake, integrate `headless.nixosModules.headless` into that flake exposing `nixosConfigurations.machine` beside `settings.json` and `headless.conf`.
- Rollback if needed: `sudo nixos-rebuild switch --rollback`.

## Optional NixOS Replacement (`nixos-anywhere`)

On non-NixOS distributions, offer `install-nixos.sh` only after explicitly warning that it **wipes the entire target disk**:

- Requirements: Nix installed locally, `x86_64` or `aarch64` target, >= 2 GB RAM, Secure Boot disabled, wired IPv4 address (DHCP or static; Wi-Fi, IPv6-only, bridge/bond/VLAN stop safely before touching disk).
- Preserves SSH host key, network address, account password hash, and public SSH key.
- Always list disks first (`install-nixos.sh DIR --list-disks`), have the user confirm the exact device path, and only then run `install-nixos.sh DIR --disk /dev/DISK --yes-wipe`.

## Common Failures

| Error | Cause and Fix |
| --- | --- |
| `is in neither the wheel nor the sudo group` | Run `usermod -aG sudo ACCOUNT` (or `wheel`) at the machine, re-login, and re-run `connect.sh`. |
| `does not read /etc/ssh/sshd_config.d` | Add `Include /etc/ssh/sshd_config.d/*.conf` at the top of `/etc/ssh/sshd_config`. |
| `another setting overrides` | Check `sudo sshd -T` and `grep -r PasswordAuthentication /etc/ssh` for an earlier conflicting file. |
| `The installer did not start` | Secure Boot is enabled or kernel lacks `kexec`; disable Secure Boot or install NixOS manually. |
| `does not power on after power cut` | Power-loss recovery and Wake-on-LAN are firmware (BIOS/UEFI) settings on Linux hardware. |
