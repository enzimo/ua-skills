import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_release", ROOT / "scripts" / "build_release.py"
)
assert SPEC and SPEC.loader
BUILD_RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD_RELEASE)


class ReleaseBuildTests(unittest.TestCase):
    def test_repository_version_is_semver(self):
        version = BUILD_RELEASE.read_version(ROOT)
        self.assertIsNotNone(BUILD_RELEASE.SEMVER.fullmatch(version))

    def test_release_tag_must_match_version(self):
        BUILD_RELEASE.verify_tag("0.1.0", "v0.1.0")
        with self.assertRaisesRegex(ValueError, "does not match"):
            BUILD_RELEASE.verify_tag("0.1.0", "v0.2.0")

    def test_skill_archives_are_reproducible(self):
        skill = ROOT / "skills" / "brave-search"
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_archive = Path(first) / "skill.zip"
            second_archive = Path(second) / "skill.zip"
            BUILD_RELEASE.archive_skill(skill, first_archive)
            BUILD_RELEASE.archive_skill(skill, second_archive)

            self.assertEqual(first_archive.read_bytes(), second_archive.read_bytes())
            with zipfile.ZipFile(first_archive) as archive:
                self.assertIn("brave-search/SKILL.md", archive.namelist())


if __name__ == "__main__":
    unittest.main()
