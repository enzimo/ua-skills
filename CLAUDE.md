# Developer / Agent Guidelines (`CLAUDE.md`)

This file guides AI agents and developers working on the `ua-skills` repository.

## Commands

- **Skill Validation:** `python skills/skill-creator/scripts/quick_validate.py skills/<skill-name>`
- **Skill Initialization:** `python skills/skill-creator/scripts/init_skill.py <skill-name> --path skills/`
- **Skill Packaging:** `python skills/skill-creator/scripts/package_skill.py skills/<skill-name>`
- **Release Tests:** `python -m unittest discover -s tests -v`
- **Release Build:** `python scripts/build_release.py --tag v$(cat VERSION)`

## Versioning and Releases

- Use Semantic Versioning and keep the canonical version in `VERSION`.
- Record user-visible changes in `CHANGELOG.md` before releasing.
- Create release tags in the exact `v<version>` form; the build rejects tags
  that do not match `VERSION`.
- Let `.github/workflows/release.yml` validate and publish deterministic
  per-skill ZIP archives and `SHA256SUMS` to GitHub Releases.

## Available Skills

The canonical list of available skills is maintained in `README.md` under "Available Skills". Update that table when adding, removing, or renaming skills under `skills/`.
The catalog includes `user-onboarding-guide` for Universal Agents first-run opt-in capability tours.
The catalog includes `single-page-site` for generated articles, comparisons,
procedural how-tos, and browser-local interactive apps.
The catalog includes `long-horizon-plan-execution` for self-sustaining execution,
domain-procedure governance, independent Objective/Plan/Task lifecycles,
objective health, and adaptive recovery. Keep its
normative requirements synchronized with
`../ua-architecture/docs/SOP-OODA-Loop.md`; allow skill-only operational
refinements only when they preserve that SOP's meaning.
The catalog's `markitdown` skill complements the Universal Agents bundled local
AnyDoc skill by owning broader formats, URLs, plugins, and OCR-related
workflows; do not blur that converter boundary with a silent fallback.

## Code Style & Skill Structure

- **Skill Directory Layout:**

  ```text
  skills/skill-name/
  ├── SKILL.md (required - contains YAML metadata and instructions)
  ├── scripts/ (optional - helper scripts)
  ├── references/ (optional - extra documentation, schemas)
  └── assets/ (optional - templates, static files)
  ```

- **YAML Frontmatter (in `SKILL.md`):**
  Must contain `name` and `description`.
  - The name must be `hyphen-case` (lowercase letters, digits, and hyphens only).
  - The description must be in the third-person and cannot contain angle brackets (`<` or `>`).

- **Writing Instructions:**
  - Write all instructions using the **imperative/infinitive form** (e.g., "To perform X, do Y" instead of "You should do X").
  - Do not use placeholders.

- **Process Rules:**
  - **No Fixes Without Root Cause First:** Never apply symptom-focused patches. Trace data flow to the original trigger and write reproducing test cases.
  - **Documentation Sync:** Always update `README.md`, `CLAUDE.md`, and `AGENTS.md` after making changes to the project to reflect the latest state.
  - **Credential Handling:** For skills that use credentials, instruct agents to check hydrated CLI/runtime auth, environment variables, secret-file mounts, or credential stores before asking for new credentials. Never instruct agents to request secrets in chat; direct users to the runtime credential collection form when new credentials are required.
  - **Universal Agents Shell Handling:** For skills that run commands, instruct agents to load `shell-execution-workflows`. Keep commands non-interactive, do not manually prefix them with `rtk`, use `work_dir` and explicit timeouts, parallelize only independent commands, inspect separated output/error and termination metadata, and preserve broker ownership of credentialed CLIs and loopback services.
- **Google Workspace Skill:** Keep `skills/gog/SKILL.md` aligned with installed `gog` command help, the broker's canonical auth methods, Google's External Testing 7-day refresh-token rule, and the `secure_cli` provider/action/params envelope, especially Gmail search/send params, `gog.exec` argv nesting, decoded-body behavior, and attachment-download behavior.
