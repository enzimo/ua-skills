import importlib.util
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "headless"
SCRIPTS_DIR = SKILL_DIR / "scripts"
VALIDATOR_PATH = ROOT / "skills" / "skill-creator" / "scripts" / "quick_validate.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("quick_validate", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


QUICK_VALIDATE = _load_validator()


class HeadlessSkillTests(unittest.TestCase):
    def test_skill_passes_quick_validate(self):
        valid, message = QUICK_VALIDATE.validate_skill(SKILL_DIR)
        self.assertTrue(valid, message)

    def test_all_shell_scripts_pass_bash_syntax_check(self):
        scripts = sorted(SCRIPTS_DIR.rglob("*.sh"))
        self.assertGreater(len(scripts), 10)
        for script in scripts:
            proc = subprocess.run(
                ["bash", "-n", str(script)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                proc.returncode,
                0,
                f"bash -n failed for {script.relative_to(ROOT)}: {proc.stderr}",
            )

    def test_secret_run_cmd_pipes_secret_without_exposing_args(self):
        proc = subprocess.run(
            [
                str(SCRIPTS_DIR / "secret-run.sh"),
                "cmd:printf 'top-secret-value'",
                "--",
                "/bin/sh",
                "-c",
                "cat <&3",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "top-secret-value")

    def test_secret_run_refuses_ua_ref_in_local_shell(self):
        proc = subprocess.run(
            [
                str(SCRIPTS_DIR / "secret-run.sh"),
                "ua:headless_box_admin",
                "--",
                "true",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Universal Agents broker", proc.stderr)

    def test_new_config_defaults_tailscale_on_and_writes_headless_conf(self):
        pubkey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMypJnmwSE7hhkQADVWGRLHsEeA6BU2Sj/TxykcHxHcP test@example.com"
        for platform in ("mac", "linux", "windows"):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as tmp:
                cfg_dir = Path(tmp) / f"box-{platform}"
                proc = subprocess.run(
                    [
                        str(SCRIPTS_DIR / platform / "new-config.sh"),
                        str(cfg_dir),
                        "--address",
                        "192.0.2.20",
                        "--login",
                        "exampleuser",
                        "--password-ref",
                        "op:op://Private/Box/password",
                        "--ssh-key-ref",
                        "op:op://Private/Box/ssh-key",
                        "--ssh-pubkey",
                        pubkey,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertTrue((cfg_dir / "headless.conf").is_file())
                self.assertFalse((cfg_dir / "headless.env").exists())
                self.assertTrue((cfg_dir / "authorized_key.pub").is_file())
                settings = json.loads((cfg_dir / "settings.json").read_text(encoding="utf-8"))
                self.assertTrue(settings["tailscale"]["enable"])
                self.assertEqual(settings["sshKeys"], [pubkey])
                conf = (cfg_dir / "headless.conf").read_text(encoding="utf-8")
                self.assertIn("SSH_KEY_REF=op:op://Private/Box/ssh-key", conf)
                self.assertIn("SSH_PUBKEY=authorized_key.pub", conf)

    def test_new_config_honors_no_tailscale_and_ssh_agent_pubkey(self):
        pubkey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMypJnmwSE7hhkQADVWGRLHsEeA6BU2Sj/TxykcHxHcP test@example.com"
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp) / "box"
            proc = subprocess.run(
                [
                    str(SCRIPTS_DIR / "linux" / "new-config.sh"),
                    str(cfg_dir),
                    "--address",
                    "192.0.2.20",
                    "--login",
                    "exampleuser",
                    "--password-ref",
                    "av:BOX_PW",
                    "--ssh-agent-pubkey",
                    pubkey,
                    "--no-tailscale",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            settings = json.loads((cfg_dir / "settings.json").read_text(encoding="utf-8"))
            self.assertFalse(settings["tailscale"]["enable"])
            conf = (cfg_dir / "headless.conf").read_text(encoding="utf-8")
            self.assertIn("SSH_AGENT_PUBKEY=authorized_key.pub", conf)

    def test_new_config_rejects_env_file_inside_config_folder(self):
        pubkey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMypJnmwSE7hhkQADVWGRLHsEeA6BU2Sj/TxykcHxHcP test@example.com"
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp) / "box"
            cfg_dir.mkdir()
            secret_file = cfg_dir / "secret.env"
            secret_file.write_text("PW=test\n", encoding="utf-8")
            os.chmod(secret_file, 0o600)
            proc = subprocess.run(
                [
                    str(SCRIPTS_DIR / "linux" / "new-config.sh"),
                    str(cfg_dir),
                    "--address",
                    "192.0.2.20",
                    "--login",
                    "exampleuser",
                    "--password-ref",
                    f"env:{secret_file}:PW",
                    "--ssh-agent-pubkey",
                    pubkey,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("outside the config folder", proc.stderr)

    def test_load_config_materializes_and_cleans_ssh_key_ref_with_passphrase(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_key = tmp_path / "source_key"
            subprocess.run(
                [
                    "ssh-keygen",
                    "-t",
                    "ed25519",
                    "-N",
                    "test-passphrase-123",
                    "-f",
                    str(raw_key),
                    "-q",
                ],
                check=True,
            )
            cfg_dir = tmp_path / "box"
            proc = subprocess.run(
                [
                    str(SCRIPTS_DIR / "linux" / "new-config.sh"),
                    str(cfg_dir),
                    "--address",
                    "192.0.2.20",
                    "--login",
                    "exampleuser",
                    "--password-ref",
                    "cmd:printf dummy",
                    "--ssh-key-ref",
                    f"cmd:cat '{raw_key}'",
                    "--ssh-passphrase-ref",
                    "cmd:printf 'test-passphrase-123'",
                    "--ssh-pubkey",
                    str(raw_key.with_suffix(".pub")),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

            # Verify load_config unlocks key into private ephemeral ssh-agent and cleans up on exit
            probe = f"""
set -euo pipefail
. "{SCRIPTS_DIR / 'mac' / 'lib.sh'}"
load_config "{cfg_dir}"
printf 'MODE=%s\\n' "$SSH_AUTH_MODE"
printf 'TEMP_DIR=%s\\n' "${{_HEADLESS_TEMP_DIRS[0]}}"
printf 'AGENT_PID=%s\\n' "$_HEADLESS_AGENT_PID"
ssh-add -L | grep -qF "$(cut -d' ' -f2 < "$SSH_PUBKEY_FILE")"
printf 'AGENT_LOADED=yes\\n'
"""
            run = subprocess.run(
                ["bash", "-c", probe],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("MODE=store", run.stdout)
            self.assertIn("AGENT_LOADED=yes", run.stdout)
            temp_dir_line = [
                line.split("=", 1)[1]
                for line in run.stdout.splitlines()
                if line.startswith("TEMP_DIR=")
            ][0]
            self.assertFalse(
                Path(temp_dir_line).exists(),
                f"Ephemeral SSH temp directory was not cleaned up: {temp_dir_line}",
            )

    def test_load_config_materializes_unencrypted_ssh_key_ref_0600_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_key = tmp_path / "source_key"
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(raw_key), "-q"],
                check=True,
            )
            cfg_dir = tmp_path / "box"
            subprocess.run(
                [
                    str(SCRIPTS_DIR / "linux" / "new-config.sh"),
                    str(cfg_dir),
                    "--address",
                    "192.0.2.20",
                    "--login",
                    "exampleuser",
                    "--password-ref",
                    "cmd:printf dummy",
                    "--ssh-key-ref",
                    f"cmd:cat '{raw_key}'",
                    "--ssh-pubkey",
                    str(raw_key.with_suffix(".pub")),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            probe = f"""
set -euo pipefail
. "{SCRIPTS_DIR / 'mac' / 'lib.sh'}"
load_config "{cfg_dir}"
printf 'KEY_PATH=%s\\n' "$SSH_KEY"
stat -c '%a' "$SSH_KEY"
"""
            run = subprocess.run(
                ["bash", "-c", probe],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            lines = run.stdout.strip().splitlines()
            key_path = Path(lines[0].split("=", 1)[1])
            self.assertEqual(lines[1].strip(), "600")
            self.assertFalse(key_path.exists())
            self.assertFalse(key_path.parent.exists())

    def test_t3_scripts_reject_invalid_options(self):
        for script_name, args in (
            ("install-fleet.sh", ["/tmp", "--platform", "bogus"]),
            ("install-fleet.sh", ["/tmp", "--platform", "linux", "--clis", "badcli"]),
            ("link-fleet.sh", ["/tmp", "--platform", "linux", "--access", "bogus"]),
            ("verify-fleet.sh", ["/tmp", "--platform", "bogus"]),
        ):
            with self.subTest(script=script_name, args=args):
                proc = subprocess.run(
                    [str(SCRIPTS_DIR / "t3" / script_name), *args],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
