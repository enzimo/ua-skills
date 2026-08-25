import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "skill-creator" / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INIT_SKILL = load_module("init_skill", SCRIPTS / "init_skill.py")
QUICK_VALIDATE = load_module("quick_validate", SCRIPTS / "quick_validate.py")
sys.modules["quick_validate"] = QUICK_VALIDATE
PACKAGE_SKILL = load_module("package_skill", SCRIPTS / "package_skill.py")


class SkillInitializerTests(unittest.TestCase):
    def test_default_initialization_creates_only_the_entrypoint(self):
        with tempfile.TemporaryDirectory() as output_dir:
            skill_dir = INIT_SKILL.init_skill("incident-triage", output_dir)

            self.assertEqual(
                sorted(path.name for path in skill_dir.iterdir()),
                ["SKILL.md"],
            )
            content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("## Completion evidence", content)
            self.assertIn("## Procedure", content)
            self.assertIn("## Failure recovery", content)
            self.assertNotIn("Capabilities-Based", content)
            self.assertNotIn("Reference/Guidelines", content)

    def test_requested_resources_are_created_without_placeholders(self):
        with tempfile.TemporaryDirectory() as output_dir:
            skill_dir = INIT_SKILL.init_skill(
                "incident-triage",
                output_dir,
                resources=("scripts", "references"),
            )

            self.assertTrue((skill_dir / "scripts").is_dir())
            self.assertTrue((skill_dir / "references").is_dir())
            self.assertFalse((skill_dir / "assets").exists())
            self.assertEqual(list((skill_dir / "scripts").iterdir()), [])
            self.assertEqual(list((skill_dir / "references").iterdir()), [])

    def test_examples_are_limited_to_requested_resources(self):
        with tempfile.TemporaryDirectory() as output_dir:
            skill_dir = INIT_SKILL.init_skill(
                "incident-triage",
                output_dir,
                resources=("references",),
                examples=True,
            )

            self.assertTrue((skill_dir / "references" / "example.md").is_file())
            self.assertFalse((skill_dir / "scripts").exists())
            self.assertFalse((skill_dir / "assets").exists())


class SkillValidatorTests(unittest.TestCase):
    def write_skill(self, root: Path, name: str, body: str) -> Path:
        skill_dir = root / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
        return skill_dir

    def test_generated_template_fails_until_completed(self):
        with tempfile.TemporaryDirectory() as output_dir:
            skill_dir = INIT_SKILL.init_skill("incident-triage", output_dir)

            valid, message = QUICK_VALIDATE.validate_skill(skill_dir)

            self.assertFalse(valid)
            self.assertIn("unfinished scaffold", message.casefold())

    def test_validator_rejects_example_placeholders(self):
        with tempfile.TemporaryDirectory() as output_dir:
            root = Path(output_dir)
            skill_dir = self.write_skill(
                root,
                "incident-triage",
                """---
name: incident-triage
description: Guides incident triage when a service alert requires diagnosis and recovery.
---

# Incident triage

Reproduce the alert, isolate the failing component, restore service, and verify recovery.
""",
            )
            references = skill_dir / "references"
            references.mkdir()
            (references / "example.md").write_text(
                "Replace with actual reference material.", encoding="utf-8"
            )

            valid, message = QUICK_VALIDATE.validate_skill(skill_dir)

            self.assertFalse(valid)
            self.assertIn("references/example.md", message)

    def test_validator_accepts_a_completed_skill(self):
        with tempfile.TemporaryDirectory() as output_dir:
            skill_dir = self.write_skill(
                Path(output_dir),
                "incident-triage",
                """---
name: incident-triage
description: Guides incident triage when a service alert requires diagnosis and recovery.
---

# Incident triage

Reproduce the alert, isolate the failing component, restore service, and verify recovery.
""",
            )

            valid, message = QUICK_VALIDATE.validate_skill(skill_dir)

            self.assertTrue(valid, message)


class SkillPackagerTests(unittest.TestCase):
    def test_packager_excludes_python_cache_artifacts(self):
        with (
            tempfile.TemporaryDirectory() as root_dir,
            tempfile.TemporaryDirectory() as output_dir,
        ):
            skill_dir = Path(root_dir) / "incident-triage"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                """---
name: incident-triage
description: Guides incident triage when a service alert requires diagnosis and recovery.
---

# Incident triage

Reproduce the alert, isolate the failing component, restore service, and verify recovery.
""",
                encoding="utf-8",
            )
            cache_dir = skill_dir / "scripts" / "__pycache__"
            cache_dir.mkdir(parents=True)
            (cache_dir / "helper.cpython-313.pyc").write_bytes(b"cache")

            archive_path = PACKAGE_SKILL.package_skill(skill_dir, output_dir)

            self.assertIsNotNone(archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
            self.assertEqual(names, ["incident-triage/SKILL.md"])


if __name__ == "__main__":
    unittest.main()
