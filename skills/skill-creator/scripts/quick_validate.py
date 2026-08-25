#!/usr/bin/env python3
"""Run structural validation for a skill package."""

import re
import sys
from pathlib import Path

FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)
VALID_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
UNFINISHED_MARKERS = (
    "TODO:",
    "Replace with actual",
    "This is a placeholder",
)
GENERATED_EXAMPLE_PATHS = (
    Path("scripts/example.py"),
    Path("references/example.md"),
    Path("assets/example.txt"),
)


def frontmatter_value(frontmatter, field):
    """Extract one single-line YAML frontmatter value."""
    match = re.search(rf"^{re.escape(field)}:\s*(.+?)\s*$", frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else None


def unfinished_scaffold(skill_path, skill_content):
    """Return the first unfinished generated file and marker, if present."""
    files = ((Path("SKILL.md"), skill_content),)
    for relative_path in GENERATED_EXAMPLE_PATHS:
        path = skill_path / relative_path
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            files += ((relative_path, content),)

    for relative_path, content in files:
        for marker in UNFINISHED_MARKERS:
            if marker.casefold() in content.casefold():
                return relative_path, marker
    return None


def validate_skill(skill_path):
    """Validate package structure and reject unfinished generated content."""
    skill_path = Path(skill_path)
    if not skill_path.is_dir():
        return False, f"Skill directory not found: {skill_path}"

    skill_md = skill_path / "SKILL.md"
    if not skill_md.is_file():
        return False, "SKILL.md not found"

    content = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER.match(content)
    if not match:
        return False, "Invalid or missing YAML frontmatter"
    frontmatter = match.group(1)

    name = frontmatter_value(frontmatter, "name")
    if not name:
        return False, "Missing or empty 'name' in frontmatter"
    if len(name) > 64:
        return False, "Name must be 64 characters or fewer"
    if not VALID_NAME.fullmatch(name):
        return False, (
            f"Name '{name}' must use lowercase letters, digits, and single hyphens "
            "between words"
        )
    if name != skill_path.name:
        return False, f"Name '{name}' must match directory '{skill_path.name}'"

    description = frontmatter_value(frontmatter, "description")
    if not description:
        return False, "Missing or empty 'description' in frontmatter"
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets (< or >)"

    unfinished = unfinished_scaffold(skill_path, content)
    if unfinished:
        relative_path, marker = unfinished
        return False, (
            f"Unfinished scaffold in {relative_path.as_posix()}: found '{marker}'"
        )

    return True, "Skill is valid"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)

    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
