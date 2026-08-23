# Agent Instructions (`AGENTS.md`)

This file guides AI agents when operating within the `ua-skills` repository.

## Repository Purpose

This repository stores and manages Universal Agents (UA) Agent Skills under the `skills/` directory.

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
Keep its runtime mapping aligned with Universal Agents Objective work sessions,
including explicit acceptance, per-session activation, safe-boundary yield, and
OODA checkpoint persistence.
The catalog's `markitdown` skill complements the Universal Agents bundled local
AnyDoc skill by owning broader formats, URLs, plugins, and OCR-related
workflows; do not blur that converter boundary with a silent fallback.

## Core Rules for Agents

1. **Systematic Debugging:**
   - Refer to Systematic Debugging whenever diagnosing or fixing issues.
   - Do not attempt a fix without finding the root cause first.
   - Always write reproducing test cases.

2. **Documentation Sync Rule:**
   - Always read `README.md`, `CLAUDE.md`, and `AGENTS.md` at the beginning of the task.
   - Always update `README.md`, `CLAUDE.md`, and `AGENTS.md` before concluding any changes to the project.

3. **Writing Skills:**
   - Use `skills/skill-creator` to bootstrap, validate, and package skills.
   - Skill instructions must be written in the **imperative/infinitive form**.
   - Frontmatter name must be `hyphen-case`, and description must be in third-person without `<` or `>` characters.
   - For skills that use credentials, instruct agents to check hydrated CLI/runtime auth, environment variables, secret-file mounts, or credential stores before requesting new credentials. Never instruct agents to request secrets in chat; direct users to the runtime credential collection form when new credentials are required.
   - Keep `skills/gog/SKILL.md` aligned with installed `gog` command help, the broker's canonical auth methods, Google's External Testing 7-day refresh-token rule, and the `secure_cli` provider/action/params envelope, especially Gmail search/send params, `gog.exec` argv nesting, decoded-body behavior, and attachment-download behavior.
   - For skills that run commands in Universal Agents, route shared process behavior through the runtime `shell-execution-workflows` skill. Keep domain skills focused on their own command flags and policy caveats; do not duplicate or contradict the shared RTK, timeout, working-directory, result, or broker-boundary contract.

4. **Versioning and Releases:**
   - Use Semantic Versioning and store the canonical version in `VERSION`.
   - Update `CHANGELOG.md` for each release.
   - Tag releases as `v<version>` with an exact match to `VERSION`.
   - Run the release tests and artifact build before pushing a release tag.
   - Publish deterministic per-skill ZIP archives and `SHA256SUMS` through the GitHub Actions release workflow.
