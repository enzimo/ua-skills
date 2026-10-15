#!/usr/bin/env python3
"""Create a new skill entrypoint and only the requested resource directories."""

import argparse
import re
import sys
from pathlib import Path

RESOURCE_TYPES = ("scripts", "references", "assets")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SKILL_TEMPLATE = """---
name: {skill_name}
description: "TODO: Describe in third person what the skill does, when it applies, and the boundary that distinguishes it from similar skills."
---

# {skill_title}

## Applicability

[TODO: Name realistic requests that should activate this procedure and near-miss requests that should not.]

## Preconditions

[TODO: List only the state, inputs, tools, permissions, or evidence required before execution.]

## Completion evidence

[TODO: Define the observable result that proves the task is complete.]

## Procedure

1. [TODO: Establish the initial state and choose the correct operating path.]
2. [TODO: Perform the work in the reliable order.]
3. [TODO: Check intermediate evidence before continuing.]
4. [TODO: Verify the final result against the completion evidence.]

## Failure recovery

[TODO: Map recognizable failure signals to retry, adaptation, escalation, or stopping actions.]

## Resources

[TODO: Link only resources needed by this procedure and state when to read or run each one. Remove this section when no resources are needed.]
"""

EXAMPLE_SCRIPT = '''#!/usr/bin/env python3
"""Replace with actual deterministic helper logic or remove this file."""


def main():
    raise NotImplementedError("Replace with actual helper logic")


if __name__ == "__main__":
    main()
'''

EXAMPLE_REFERENCE = """# Example reference

Replace with actual decision-changing reference material or remove this file.

Link this file from SKILL.md and state when to read it.
"""

EXAMPLE_ASSET = """Replace with an actual output asset or remove this file.

Keep assets out of the instruction context unless the task requires inspecting them.
"""

EXAMPLE_FILES = {
    "scripts": ("example.py", EXAMPLE_SCRIPT, 0o755),
    "references": ("example.md", EXAMPLE_REFERENCE, None),
    "assets": ("example.txt", EXAMPLE_ASSET, None),
}


def title_case_skill_name(skill_name):
    """Convert a hyphenated skill name to a display title."""
    return " ".join(word.capitalize() for word in skill_name.split("-"))


def normalize_resources(resources):
    """Return unique resource names in the canonical directory order."""
    requested = set(resources or ())
    unsupported = requested.difference(RESOURCE_TYPES)
    if unsupported:
        names = ", ".join(sorted(unsupported))
        raise ValueError(f"Unsupported resource type: {names}")
    return tuple(resource for resource in RESOURCE_TYPES if resource in requested)


def validate_skill_name(skill_name):
    """Return a validation error for an unusable skill name, if any."""
    if len(skill_name) > 64:
        return "Skill name must be 64 characters or fewer"
    if not SKILL_NAME.fullmatch(skill_name):
        return (
            "Skill name must use lowercase letters, digits, and single hyphens "
            "between words"
        )
    return None


def init_skill(skill_name, path, *, resources=(), examples=False):
    """Initialize a skill and return its directory, or None after a reported error."""
    name_error = validate_skill_name(skill_name)
    if name_error:
        print(f"Error: {name_error}")
        return None

    try:
        requested_resources = normalize_resources(resources)
    except ValueError as exc:
        print(f"Error: {exc}")
        return None

    if examples and not requested_resources:
        print("Error: --examples requires at least one --resources value")
        return None

    skill_dir = Path(path).resolve() / skill_name
    if skill_dir.exists():
        print(f"Error: Skill directory already exists: {skill_dir}")
        return None

    try:
        skill_dir.mkdir(parents=True, exist_ok=False)
        skill_title = title_case_skill_name(skill_name)
        (skill_dir / "SKILL.md").write_text(
            SKILL_TEMPLATE.format(
                skill_name=skill_name,
                skill_title=skill_title,
            ),
            encoding="utf-8",
        )

        for resource in requested_resources:
            resource_dir = skill_dir / resource
            resource_dir.mkdir()
            if examples:
                filename, content, mode = EXAMPLE_FILES[resource]
                example_path = resource_dir / filename
                example_path.write_text(content, encoding="utf-8")
                if mode is not None:
                    example_path.chmod(mode)
    except OSError as exc:
        print(f"Error creating skill: {exc}")
        return None

    print(f"Created skill '{skill_name}' at {skill_dir}")
    print("Next steps:")
    print("1. Replace every unfinished scaffold marker in SKILL.md.")
    if examples:
        print("2. Replace or remove every generated example file.")
        validation_step = 3
    else:
        validation_step = 2
    print(f"{validation_step}. Run quick_validate.py against the skill directory.")
    return skill_dir


def parse_resources(value):
    """Parse a comma-separated resource list for argparse."""
    resources = tuple(part.strip() for part in value.split(",") if part.strip())
    unsupported = set(resources).difference(RESOURCE_TYPES)
    if unsupported:
        choices = ", ".join(RESOURCE_TYPES)
        raise argparse.ArgumentTypeError(
            f"unsupported resource type; choose from: {choices}"
        )
    return resources


def build_parser():
    parser = argparse.ArgumentParser(
        description="Create a concise skill entrypoint and optional resources."
    )
    parser.add_argument("skill_name", help="Hyphen-case skill name")
    parser.add_argument("--path", required=True, help="Parent output directory")
    parser.add_argument(
        "--resources",
        type=parse_resources,
        default=(),
        metavar="LIST",
        help="Comma-separated subset of scripts,references,assets",
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Add unfinished examples only inside requested resource directories",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.examples and not args.resources:
        parser.error("--examples requires --resources")

    result = init_skill(
        args.skill_name,
        args.path,
        resources=args.resources,
        examples=args.examples,
    )
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
