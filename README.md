# UA Skills (`ua-skills`)

A curated collection of modular, reusable, self-contained **Universal Agents (UA) Skills**. These skills extend the capabilities of AI coding assistants and agents with specialized domain knowledge, custom workflows, tool integrations, and bundled helper scripts.

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
| **`brave-search`** | Uses Brave Search API for independent-index web search, LLM grounding context, freshness filters, Goggles ranking, and provider comparison workflows. |
| **`build-project-room`** | Prepares gated project rooms for high-stakes, multi-source knowledge work from messy or conflicting source material. |
| **`bw`** | Uses Bitwarden through the `bw` CLI or brokered secure CLI actions for auth, credential search, metadata lookup, and secret use. |
| **`crawl4ai`** | Crawls and scrapes web content through the hosted Crawl4AI service, producing clean Markdown with JS rendering and content filtering support. |
| **`gh`** | Uses GitHub from a terminal-only environment through `gh` or brokered secure CLI actions for repositories, issues, PRs, Actions, releases, search, and API calls. |
| **`gog`** | Uses Google Workspace through `gog` or brokered secure CLI actions for Gmail, Calendar, Drive, Docs, Sheets, Contacts, Admin, and related Google workflows, including durable OAuth publishing guidance, the primary manual web flow, the `secure_cli` provider/action/params envelope, decoded Gmail body, and attachment handling. |
| **`markitdown`** | Converts local documents and supported URLs to Markdown with Microsoft's MarkItDown across PDFs, Office files, HTML, CSV, JSON, XML, images, audio, ZIPs, EPubs, and more. |
| **`searxng-search`** | Searches the web through a privacy-respecting SearXNG metasearch instance for web, news, image, video, and specialized queries. |
| **`single-page-howto-site`** | Builds Universal Agents-styled single-page procedural guidance sites with materials, tools, safety notes, ordered checklists, plans, and follow-up chat. |
| **`skill-creator`** | Guides creation or updates of skills that extend an agent with specialized knowledge, workflows, tool integrations, and validation/package tooling. |
| **`systematic-debugging`** | Applies a four-phase debugging methodology with root cause analysis before fixes. |
| **`user-onboarding-guide`** | Guides early Universal Agents conversations with a warm opt-in capability tour, relatable examples, documentation links, finish handling, and remembered progress. |

---

## 🚀 Creating & Validating Skills

To create a new skill or validate an existing one, use the tooling provided by `skill-creator`:

### 1. Initialize a Skill
Run the initialization helper script to generate the directory structure and the template `SKILL.md`:
```bash
python skills/skill-creator/scripts/init_skill.py <skill-name> --path skills/
```

### 2. Validate a Skill
Ensure that the skill's name and description follow the naming conventions and structure:
```bash
python skills/skill-creator/scripts/quick_validate.py skills/<skill-name>
```

### 3. Package a Skill
Generate a packaged ZIP file for distribution:
```bash
python skills/skill-creator/scripts/package_skill.py skills/<skill-name>
```

---

## 🎯 Guiding Principles

- **No Fixes Without Root Cause First:** When resolving bugs, developers and agents must trace the data flow to the original trigger and write a reproducing test case before attempting any fixes. Refer to Systematic Debugging for more details.
- **Documentation Sync:** Always update `README.md`, `CLAUDE.md`, and `AGENTS.md` whenever adding or modifying files or introducing new architecture patterns.
- **Credential Handling:** Skills that use credentials must instruct agents to check already hydrated CLI/runtime auth, environment variables, secret-file mounts, or credential stores before requesting new credentials. Agents must never ask users to paste secrets into chat; when new credentials are needed, direct users to the runtime credential collection form.
- **Universal Agents Shell Handling:** Command-oriented skills must direct agents to the runtime `shell-execution-workflows` skill. Domain instructions should add only relevant command flags and policy caveats, leaving RTK selection, non-interactive execution, timeouts, working directories, result interpretation, credentialed CLI blocking, and loopback blocking to the shared runtime contract.

---

## 📄 License

This repository is licensed under the MIT License. Copyright (c) 2026 Enzimo.
