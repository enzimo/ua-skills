# Tailscale (Strongly Recommended, Enabled by Default)

Strongly recommend Tailscale on every headless machine and keep `"tailscale": { "enable": true }` enabled by default unless the user explicitly opts out (`--no-tailscale`) or macOS already runs `/Applications/Tailscale.app`.

## Why Tailscale Is Strongly Recommended

- **Zero exposed ports**: Reach the headless machine reliably from any network (home, office, mobile, cloud) over WireGuard without port forwarding or public SSH exposure.
- **Stable addressing**: MagicDNS names and `100.x.y.z` tailnet IPs survive router reboots and DHCP lease changes.
- **Native T3 Code fleet transport**: Unlocks `t3 pair --tailscale` (Tailscale Serve HTTPS), allowing local and remote T3 Code servers to link over private tailnet HTTPS without exposing LAN ports or depending solely on external relays.

## Platform Behavior

- **macOS (Apple silicon)**:
  - Runs the open-source `tailscaled` daemon managed by `nix-darwin`, starting automatically at every boot with no GUI app required.
  - **Existing app guard**: If `/Applications/Tailscale.app` is already installed on the Mac, do **not** run a competing `tailscaled`. Keep `"tailscale": { "enable": false }` (`--no-tailscale`) and use the existing Tailscale app instead (`apply.sh` and `tailscale.sh` refuse to start a second daemon when `/Applications/Tailscale.app` exists).
- **Linux**:
  - On NixOS, `headless.nixosModules.headless` enables `services.tailscale`.
  - On Debian, Ubuntu, and Fedora, `apply.sh` installs Tailscale from Tailscale's signed package repository and enables `tailscaled`. An existing Tailscale installation is preserved.
- **Windows (11 or Server 2025)**:
  - `apply.sh` installs Tailscale (pinned installer, SHA-256 verified) in unattended mode (`UnattendedMode = always` under `HKLM\SOFTWARE\Policies\Tailscale`) so it connects at boot before anyone signs in.
  - An existing Tailscale installation is kept and switched to unattended policy. If another Windows account already joined it without unattended mode, it signs out on restart so `tailscale.sh` can join it under the headless admin account (or ask the user before running `tailscale.sh DIR --uninstall`).

## Joining the Tailnet

After `apply.sh` completes, run `$SKILL/scripts/<platform>/tailscale.sh ~/headless/<name>`:

1. **Auth key from the credential store (zero-click, preferred for repeatable setups)**:
   - Generate a Tailscale auth key in the Tailscale admin console (`Settings > Keys`) and save it in the credential store (`references/secrets.md`).
   - Pass `--tailscale-key-ref ENTRY` to `new-config.sh` (or set `TAILSCALE_KEY_REF` in `headless.conf`).
   - `tailscale.sh` pipes the auth key on file descriptor 4 to the remote host, writes it to a root-only temporary file deleted right after `tailscale up`, and verifies `BackendState == Running`.
2. **Interactive sign-in link (no pre-created auth key needed)**:
   - Leave `TAILSCALE_KEY_REF` empty; `tailscale.sh` prints a login URL.
   - Show the link to the user to approve in their browser, then run:
     ```sh
     $SKILL/scripts/<platform>/tailscale.sh ~/headless/<name> --wait
     ```
     which waits up to 10 minutes until the tailnet IP is active.

## Switch Future Management to the Tailscale Address

Once Tailscale reports `Running` with its `100.x.y.z` IP (or MagicDNS hostname):

1. Offer to update `ADDRESS` in `headless.conf` to the Tailscale IP or MagicDNS name so future `apply.sh`, `verify.sh`, `restart.sh`, and T3 fleet commands work from anywhere, not just the initial LAN.
2. Re-run `connect.sh` once after updating `ADDRESS` to verify the pinned ed25519 host key matches the same machine over Tailscale (confirm fingerprint before replacing `known_hosts` if the address line changes).

## Custom Control Server (Headscale)

To join a self-hosted control server such as Headscale, pass `--tailscale-login-server https://headscale.example.com` to `new-config.sh` (or set `TAILSCALE_LOGIN_SERVER` in `headless.conf`).

## Opting Out or Turning Off

If the user explicitly declines Tailscale or their network forbids it, pass `--no-tailscale` to `new-config.sh` (or set `"tailscale": { "enable": false }` in `settings.json` and re-run `apply.sh`), and remove the node in the Tailscale admin console if previously joined.
