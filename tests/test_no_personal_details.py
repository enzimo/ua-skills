"""Tracked files carry no real contact details or personal host paths.

Everything tracked ships to other people: this repository is public, release
archives contain every skill file, and Universal Agents instances clone the
catalog. README.md ("Personal Details") lists what stays out and which made-up
placeholders to use. These checks catch what a machine can recognize without a
list of real values: email addresses outside reserved example domains, phone
numbers outside the fictional 555 ranges, and home folder paths with a real
account name. Names, handles and copied chats still need a reviewer.

Sample values in this file are assembled at run time so the scan of this file
itself stays clean.
"""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULES = "see README.md, Personal Details"

# A local part right after ":" or "/" is a URL's user info
# (https://user:secret@host), not an address.
EMAIL = re.compile(r"(?<![\w.%+:/-])[A-Za-z0-9._%+-]+@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})\b")
# Domains reserved for examples (RFC 2606, RFC 6761) or private networks.
EXAMPLE_DOMAINS = ("example.com", "example.net", "example.org")
EXAMPLE_TOP_LEVEL_DOMAINS = ("example", "test", "invalid", "localhost", "internal", "local")
# GitHub's own shared addresses; personal noreply addresses name a login.
SHARED_ADDRESSES = frozenset({"git@github.com", "noreply@github.com"})

PHONE = re.compile(r"(?<![\w.+/-])\+[1-9][\d ().-]{8,18}\d")
# North American numbers set aside for examples: area code 555, or the
# 555-0100 to 555-0199 lines in any area code.
FICTIONAL_PHONE = re.compile(r"1555\d{7}|1\d{3}55501\d{2}")

HOME_FOLDER = re.compile(r"(?:/home/|/Users/|[A-Za-z]:\\+Users\\+)([A-Za-z0-9._-]+)")
# Generic accounts: placeholders, container users and shared folders.
GENERIC_ACCOUNTS = frozenset(
    {
        "person",
        "user",
        "username",
        "you",
        "example",
        "exampleuser",
        "developer",
        "runner",
        "node",
        "ubuntu",
        "shared",
        "public",
    }
)


def _is_example_email(address):
    domain = address.rsplit("@", 1)[1].lower()
    if address.lower() in SHARED_ADDRESSES:
        return True
    if any(domain == example or domain.endswith(f".{example}") for example in EXAMPLE_DOMAINS):
        return True
    return domain.rsplit(".", 1)[-1] in EXAMPLE_TOP_LEVEL_DOMAINS


def _is_real_phone(number):
    digits = re.sub(r"\D", "", number)
    if not 10 <= len(digits) <= 15:
        return False  # Too short or long for a phone number: versions, offsets, counts.
    return FICTIONAL_PHONE.fullmatch(digits) is None


def personal_details(text):
    """Return each real-looking address, phone number or home path in text."""
    found = [match.group(0) for match in EMAIL.finditer(text) if not _is_example_email(match.group(0))]
    found += [match.group(0) for match in PHONE.finditer(text) if _is_real_phone(match.group(0))]
    found += [
        match.group(0)
        for match in HOME_FOLDER.finditer(text)
        if match.group(1).lower() not in GENERIC_ACCOUNTS
    ]
    return found


def tracked_personal_details(project_root=ROOT):
    # Only tracked files ship; local builds and ignored files stay out.
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=project_root,
        check=True,
        capture_output=True,
    ).stdout.decode()
    findings = []
    for relative_path in filter(None, tracked.split("\0")):
        path = project_root / relative_path
        if not path.is_file():
            continue  # Deleted in the working tree but not yet committed.
        content = path.read_bytes()
        if b"\0" in content:
            continue  # Binary file.
        for number, line in enumerate(content.decode("utf-8", errors="replace").splitlines(), start=1):
            findings += [f"{relative_path}:{number}: {detail}" for detail in personal_details(line)]
    return findings


AT = "@"


class PersonalDetailsTests(unittest.TestCase):
    def test_tracked_files_have_no_personal_details(self):
        if not (ROOT / ".git").exists():
            self.skipTest("not a Git checkout, so there is no list of tracked files")
        self.assertEqual(tracked_personal_details(), [], RULES)

    def test_real_looking_details_are_found(self):
        for text in [
            f"write to pat{AT}mailbox.co",
            f"Pat <pat.lee+ci{AT}corp.example.co.uk>",
            f"1234+pat{AT}users.noreply.github.com",
            f"gog --account pat{AT}gmail.com",
            "call +49 30 " + "1234 5678",
            "text +1 (312) " + "867-5309",
            "cd /home/" + "pat/projects",
            "open /Users/" + "pat.lee/Desktop",
            r"C:\\Users\\" + "pat\\repo",
        ]:
            with self.subTest(text=text):
                self.assertNotEqual(personal_details(text), [])

    def test_placeholders_and_non_contact_text_pass(self):
        for text in [
            f"alice{AT}example.com, bob{AT}mail.example.net, ops{AT}acme.example",
            f"person{AT}team.test and nobody{AT}example.invalid",
            f"git clone git{AT}github.com:example-owner/repo.git",
            f"https://user:secret{AT}api.vendor.com/v1",
            f"https://token{AT}github.com/example/skills",
            "+15551234567, +1 555 000 0001, +1 415-555-0132",
            "version +1.2.3, offset +05:00, count +12345, date 2026-10-14T12:00:00+00:00",
            "/home/node/app, /home/runner/work, /Users/Shared, /Users/developer/project, /home/<user>/repo",
            f"{AT}decorator and npm {AT}scope/package{AT}1.2.3",
        ]:
            with self.subTest(text=text):
                self.assertEqual(personal_details(text), [])

    def test_scan_reads_only_tracked_files(self):
        real_address = f"pat{AT}mailbox.co"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tracked.md").write_text(f"contact {real_address}\n", encoding="utf-8")
            (root / "local.env").write_text(f"OWNER={real_address}\n", encoding="utf-8")
            (root / "image.bin").write_bytes(f"\0{real_address}".encode())
            subprocess.run(["git", "init", "--quiet", str(root)], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "add", "tracked.md", "image.bin"],
                check=True,
                capture_output=True,
            )

            self.assertEqual(tracked_personal_details(root), [f"tracked.md:1: {real_address}"])


if __name__ == "__main__":
    unittest.main()
