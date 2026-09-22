# UA Skills (`ua-skills`)

A curated collection of modular, reusable, self-contained **Universal Agents (UA) Skills**. These skills stabilize agent execution with scoped procedures, decision points, checkpoints, recovery paths, and only the supporting resources required by the workflow.

---

## 🛠️ The Anatomy of a Skill

Each skill is structured under the `skills/` directory following a standardized blueprint:

```text
skills/skill-name/
├── SKILL.md (required)      # Contains YAML metadata and agent instructions
├── scripts/ (optional)      # Deterministic scripts (Python, Bash, etc.)
├── references/ (optional)   # Extra reference materials (schemas, policies, etc.)
└── assets/ (optional)       # Templates, boilerplate, and static resources
```

- **YAML Frontmatter:** Defined at the top of each `SKILL.md` to help the assistant locate and trigger the skill dynamically.
- **Progressive Disclosure:** Keeps the assistant's context window lean. Only basic metadata is loaded initially. Detailed instructions are loaded when the skill is active, and bundled resources are loaded or executed on-demand.

---

## 📚 Available Skills

Below is a summary of the skills currently available in this repository:

| Skill | Description |
| :--- | :--- |
| **`xurl`** | Publishes X text posts through the credential broker and checks the selected account. |
| **`hf-cli`** | Searches Hugging Face models/datasets and performs bounded brokered file transfers. |
| **`brave-search`** | Uses Brave Search API for independent-index web search, LLM grounding context, freshness filters, Goggles ranking, and provider comparison workflows. |
| **`build-project-room`** | Prepares gated project rooms for high-stakes, multi-source knowledge work from messy or conflicting source material. |
| **`bw`** | Uses Bitwarden through the `bw` CLI or brokered secure CLI actions for auth, credential search, metadata lookup, and secret use. |
| **`crawl4ai`** | Coordinates MCP setup, stored-credential consent and Inbox review, then uses the available Crawl4AI tools for rendered retrieval, extraction, screenshots, PDFs, and crawl workflows. |
| **`long-horizon-plan-execution`** | Guides self-sustaining teams through goal contracts, independent Objective/Plan/Task lifecycles, evolving completion criteria, actionable-frontier planning, level-specific progress definitions, supervised replanning, selective alternatives, negotiated work sessions, adaptive OODA execution, recovery, and evidence-based closure. |
| **`gh`** | Uses GitHub from a terminal-only environment through `gh` or brokered secure CLI actions for repositories, issues, PRs, Actions, releases, search, and API calls. |
| **`gog`** | Uses Google Workspace through `gog` or brokered secure CLI actions for Gmail, Calendar, Drive, Docs, Sheets, Contacts, Admin, and related Google workflows, including durable OAuth publishing guidance, the primary manual web flow, renamed-account recovery, the `secure_cli` provider/action/params envelope, decoded Gmail body, and attachment handling. |
| **`markitdown`** | Handles URLs, HTML, JSON/XML, images, audio, archives, Outlook, YouTube, plugins, OCR-related workflows, and other conversion needs outside Universal Agents' bundled local AnyDoc format set. |
| **`searxng-search`** | Searches the web through a privacy-respecting SearXNG metasearch instance for web, news, image, video, and specialized queries. |
| **`single-page-site`** | Builds Universal Agents-styled single-page articles, comparisons, how-tos, and interactive apps with optional structured UI and follow-up chat. |
| **`skill-creator`** | Guides creation and iterative improvement of effective skills through concrete examples, reusable resources, progressive disclosure, packaging, and feedback. |
| **`systematic-debugging`** | Applies a four-phase debugging methodology with root cause analysis before fixes. |
| **`user-onboarding-guide`** | Guides early Universal Agents conversations with a warm opt-in capability tour, relatable examples, documentation links, finish handling, and remembered progress. |

---

## 🚀 Creating & Validating Skills

To create a new skill or validate an existing one, use the tooling provided by `skill-creator`:

### 1. Initialize a Skill

Run the initialization helper to create a concise procedural `SKILL.md` template:

```bash
python skills/skill-creator/scripts/init_skill.py <skill-name> --path skills/
```

Request only the resource directories the skill needs. Add unfinished examples
only when they will be replaced during the same authoring workflow:

```bash
python skills/skill-creator/scripts/init_skill.py <skill-name> --path skills/ \
  --resources scripts,references
python skills/skill-creator/scripts/init_skill.py <skill-name> --path skills/ \
  --resources references --examples
```

### 2. Validate a Skill

Check frontmatter, naming, directory identity, and unfinished generated content:

```bash
python skills/skill-creator/scripts/quick_validate.py skills/<skill-name>
```

### 3. Package a Skill

Generate a packaged ZIP file for distribution:

```bash
python skills/skill-creator/scripts/package_skill.py skills/<skill-name>
```

## 📦 Versioning & Releases

The repository uses [Semantic Versioning](https://semver.org/). The current
version is stored in `VERSION`, and notable changes are recorded in
`CHANGELOG.md`.

To prepare a release, update `VERSION` and `CHANGELOG.md`, then verify the
release artifacts locally:

```bash
python -m unittest discover -s tests -v
python scripts/build_release.py --tag v$(cat VERSION)
```

Pushes and pull requests are validated by GitHub Actions. Pushing the matching
`v<version>` tag starts the release workflow, which validates every skill and
publishes one deterministic ZIP archive per skill together with `SHA256SUMS`.
Re-running the workflow replaces the assets on the existing release instead of
creating a duplicate.

---

## 🎯 Guiding Principles

- **No Fixes Without Root Cause First:** When resolving bugs, developers and agents must trace the data flow to the original trigger and write a reproducing test case before attempting any fixes. Refer to Systematic Debugging for more details.
- **Procedural Anchoring:** Use concrete examples to capture the workflow, then retain the decisions, sequence, checks, and recovery guidance that make repeated execution reliable. Keep generic facts and copied manuals out of the entrypoint.
- **Behavioral Verification:** Compare observable task outcomes when materially revising a skill. Include similar-skill distractors and out-of-scope near-misses when routing quality matters; treat structural validation as a packaging gate rather than proof of skill quality.
- **Documentation Sync:** Always update `README.md`, `CLAUDE.md`, and `AGENTS.md` whenever adding or modifying files or introducing new architecture patterns.
- **Credential Handling:** Skills that use credentials must instruct agents to check already hydrated CLI/runtime auth, environment variables, secret-file mounts, or credential stores before requesting new credentials. Agents must never ask users to paste secrets into chat; when new credentials are needed, direct users to the runtime credential collection form.
- **Authorization Wording:** In user-facing replies, name the concrete server,
  tool, agent, credential, or action. State what did not happen, why, and the next
  useful step when access is denied or an action fails. Keep attach, invoke,
  grant, lease, consumed, and revoke as internal terms unless the user asks for
  technical details.
- **Universal Agents Shell Handling:** Command-oriented skills must direct agents to the runtime `shell-execution-workflows` skill. Domain instructions should add only relevant command flags and policy caveats, leaving RTK selection, non-interactive execution, timeouts, working directories, result interpretation, credentialed CLI blocking, and loopback blocking to the shared runtime contract.
- **OODA Governance Sync:** Keep normative requirements in `long-horizon-plan-execution` synchronized with `ua-architecture/docs/SOP-OODA-Loop.md`, including actionability by Plan branch, progress definitions at each planning level, and higher-order or human control of material replanning. Allow faster skill-only refinement of examples, templates, routing instructions, and operational heuristics only when it does not weaken or redefine the canonical SOP.
- **Objective Work Sessions:** Keep the skill's Universal Agents runtime mapping aligned with opt-in activation, built-in and private profile selection, exact custom-profile acceptance, safe-yield, and checkpoint behavior without treating the skill as authority.
- **Evaluated Alternatives:** Keep bounded solution variation discretionary, advisory, and separate from workspace isolation, effect authorization, integration, and final verification.
- **Document Conversion Boundaries:** Prefer the bundled local Rust AnyDoc skill
  for its supported Office, OpenDocument, RTF, EPUB, CSV, and text-based PDF
  formats. Keep `markitdown` focused on broader formats, URLs, plugins, and OCR-
  related workflows, and never hide a converter change behind a fallback.

---

## 📄 License

This repository is licensed under the MIT License. Copyright (c) 2026 Enzimo.

Use the existing `builtin:x_posting` capability for reviewed specialist X access.
Keep its credential binding and invocation consent separate; do not route missing
X access through an unrelated delegation-envelope registration request.

Keep the long-horizon runtime mapping aligned with automatic scheduled workers,
prospective tool readiness, and schedule-specific access approval. Preserve the
separate protected Objective work-session workflow.
Treat automatic-start eligibility as TeamLead-managed through bounded runtime
settings; retain operator control of explicit denies, the kill switch and limits.
The runtime mapping runs memory timers locally with MemReviewAgent and documents
the offline upgrade for old TeamArchitect timers. Queued review records survive
the upgrade; claimed reviews and saved worker tasks require outcome checks first.
The mapping also checks saved approval outcomes before proposing repairs.
It also keeps review batches on one task and distinguishes missing review items
from decisions still awaiting the user.

Keep delegation-boundary comparison and unfinished review-step correction aligned
with the runtime mapping. Preserve saved Inbox reviews across workflow-link errors
and use tool-returned workflow URLs instead of guessing runtime-skill docs pages.

The runtime mapping covers duplicate permission reviews resolved from existing
access. Continue from the verified current result without asking for another
approval or treating the resolution as new access or an expiry extension.

Keep the runtime mapping aligned with quiet recurring checks that preserve
conversation history, explicit follow-up response obligations, and the separate
built-in guidance and saved-workflow progress URLs.

Keep permission-review guidance aligned with the shared Inbox pending-review
records. Raw historical requests must not reopen completed owner decisions.

The long-horizon runtime mapping also covers abandoned memory-review claims:
explicit offline retirement, retained unknown outcomes, and InternalImprovementAgent
cleanup with permission checks and retention.

The long-horizon runtime mapping includes bounded schedule and memory-review
inspection: use summaries for discovery and exact IDs for paged source details.

Task-backlog recovery uses owner-scoped Settings task controls. Queue purge keeps
current work; `/stop all` cancels it too. Both retain future schedules and history.
After a control timeout, inspect current task state before retrying cancellation.
Bounded Objective sessions close their Tasks after checkpointing; remaining plan
work belongs to later sessions. A raw permission request does not prove Inbox delivery.

For session-completion verification failures, inspect the saved policy and schedule
link, preserve checkpoints, and explicitly resume a blocked Objective after repair.


Task-backlog guidance uses Settings → Tasks to inspect work grouped by running
agent. **Purge this queue** applies to the selected agent's queued and waiting work
and preserves current work. /stop continues to inspect the TeamLead task trees.
