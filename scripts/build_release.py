#!/usr/bin/env python3
"""Validate and build deterministic release archives for every skill."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def read_version(root: Path = ROOT) -> str:
    """Read and validate the repository version."""
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not SEMVER.fullmatch(version):
        raise ValueError(f"VERSION is not valid Semantic Versioning: {version!r}")
    return version


def verify_tag(version: str, tag: str | None) -> None:
    """Require a supplied release tag to match VERSION exactly."""
    if tag is not None and tag != f"v{version}":
        raise ValueError(f"tag {tag!r} does not match VERSION {version!r}")


def validate_skill(root: Path, skill: Path) -> None:
    """Run the repository's canonical validator for one skill."""
    validator = root / "skills" / "skill-creator" / "scripts" / "quick_validate.py"
    subprocess.run([sys.executable, str(validator), str(skill)], check=True)


def archive_skill(skill: Path, destination: Path) -> None:
    """Write one skill archive with stable ordering, metadata, and timestamps."""
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for source in sorted(path for path in skill.rglob("*") if path.is_file()):
            relative = source.relative_to(skill.parent).as_posix()
            info = zipfile.ZipInfo(relative, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
            info.external_attr = (mode & 0xFFFF) << 16
            archive.writestr(info, source.read_bytes(), compresslevel=9)


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release(root: Path, output_dir: Path, tag: str | None = None) -> list[Path]:
    """Validate all skills and create the complete release artifact set."""
    version = read_version(root)
    verify_tag(version, tag)

    skills = sorted(
        path for path in (root / "skills").iterdir() if (path / "SKILL.md").is_file()
    )
    if not skills:
        raise ValueError("no skills found to package")

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in [*output_dir.glob("*.zip"), output_dir / "SHA256SUMS"]:
        if stale.exists():
            stale.unlink()

    artifacts: list[Path] = []
    for skill in skills:
        validate_skill(root, skill)
        artifact = output_dir / f"{skill.name}-{version}.zip"
        archive_skill(skill, artifact)
        artifacts.append(artifact)

    checksums = output_dir / "SHA256SUMS"
    checksums.write_text(
        "".join(f"{sha256(artifact)}  {artifact.name}\n" for artifact in artifacts),
        encoding="utf-8",
    )
    artifacts.append(checksums)
    return artifacts


def main() -> int:
    """Parse command-line arguments and build the release."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="release tag, which must equal v<VERSION>")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()

    try:
        artifacts = build_release(ROOT, args.output.resolve(), args.tag)
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"release build failed: {error}", file=sys.stderr)
        return 1

    for artifact in artifacts:
        print(artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
