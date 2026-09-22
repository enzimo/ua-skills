# Developer / Agent Guidelines (`CLAUDE.md`)

This file guides AI agents and developers working on the `ua-skills` repository.

Keep Crawl4AI setup aligned with `activate_mcp_connection`: installation and
discovery can require separate administrator Inbox decisions. Do not describe a
raw pending permission request as an actionable Inbox item.
For stored Crawl4AI tokens, use the existing MCP credential-binding consent flow
before activation. Never treat an OpenShell lease as MCP authority or copy its
token into configuration.

## Commands

- **Skill Validation:** `python skills/skill-creator/scripts/quick_validate.py skills/<skill-name>`
- **Skill Initialization:** `python skills/skill-creator/scripts/init_skill.py <skill-name> --path skills/ [--resources scripts,references,assets] [--examples]`
- **Skill Packaging:** `python skills/skill-creator/scripts/package_skill.py skills/<skill-name>`
- **Skill-Creator Tests:** `python -m unittest tests.test_skill_creator -v`
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
evolving completion criteria, actionable-frontier planning, level-specific
progress definitions, objective health, and adaptive recovery. Keep its
normative requirements synchronized with
`../ua-architecture/docs/SOP-OODA-Loop.md`; allow skill-only operational
refinements only when they preserve that SOP's meaning.
Keep material replanning under the designated Plan owner, higher-order agent,
or human rather than allowing Task-local optimization to redefine the parent
outcome.
Keep its runtime mapping aligned with Universal Agents Objective work sessions,
including explicit acceptance, per-session activation, built-in and private
profile selection, exact custom-profile proposal acceptance, safe-boundary
yield, OODA checkpoint persistence, and closure of each session's Task without
keeping it waiting for the next timer tick. Distinguish raw permission requests
from human interaction records actually available in Inbox.
Keep completion-failure recovery explicit: preserve checkpoints, verify the saved
Objective policy/schedule link and resume a blocked Objective after repair.
Keep selective solution variation bounded and discretionary. Treat recorded
candidate evaluations and selections as advisory; they do not isolate mutable
work, authorize effects, apply a route, or replace post-integration verification.
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
  - Start with concrete usage examples, identify reusable contents from them, and iterate against observed results.
  - Treat skills as procedural anchors for capable agents. Define applicability, completion evidence, ordered decisions, checkpoints, recovery, and invalidating assumptions when those elements stabilize execution.
  - Keep discovery metadata concise and discriminating. Test similar-skill distractors and out-of-scope near-misses when materially changing routing behavior.
  - Create `scripts/`, `references/`, and `assets/` only when they have a concrete execution role. Request them explicitly from the initializer and load references only when the current path needs them.

- **Process Rules:**
  - **No Fixes Without Root Cause First:** Never apply symptom-focused patches. Trace data flow to the original trigger and write reproducing test cases.
  - **Behavioral Skill Verification:** Treat `quick_validate.py` as a structural gate only. Compare observable task outcomes for substantial skill revisions and prefer evidence from real successful and failed trajectories over generic advice.
  - **Documentation Sync:** Always update `README.md`, `CLAUDE.md`, and `AGENTS.md` after making changes to the project to reflect the latest state.
  - **Credential Handling:** For skills that use credentials, instruct agents to check hydrated CLI/runtime auth, environment variables, secret-file mounts, or credential stores before asking for new credentials. Never instruct agents to request secrets in chat; direct users to the runtime credential collection form when new credentials are required.
  - **Authorization Wording:** In user-facing replies, name the concrete server,
    tool, agent, credential, or action. On denial or failure, state what did not
    happen, why, and the next useful step. Keep attach, invoke, grant, lease,
    consumed, and revoke in technical details.
  - **Universal Agents Shell Handling:** For skills that run commands, instruct agents to load `shell-execution-workflows`. Keep commands non-interactive, do not manually prefix them with `rtk`, use `work_dir` and explicit timeouts, parallelize only independent commands, inspect separated output/error and termination metadata, and preserve broker ownership of credentialed CLIs and loopback services.
- **Google Workspace Skill:** Keep `skills/gog/SKILL.md` aligned with installed `gog` command help, the broker's canonical auth methods, Google's External Testing 7-day refresh-token rule, and the `secure_cli` provider/action/params envelope, especially Gmail search/send params, `gog.exec` argv nesting, decoded-body behavior, and attachment-download behavior.
  Preserve the account check when documenting renamed-account recovery; use
  Google's reported email only when it belongs to the user's intended account.

The `xurl` and `hf-cli` skills pair with Universal Agents bundled templates.
Keep their broker envelopes and versioned command references synchronized with
`../universal-agents`, using `python -m scripts.sync_hub_cli_skills --check`
from that checkout. Authenticated operations use the broker; do not instruct
agents to copy Sealbox values into their own shell environments.

Use the existing `builtin:x_posting` capability for reviewed specialist X access.
Keep its credential binding and invocation consent separate; do not route missing
X access through an unrelated delegation-envelope registration request.

Keep the long-horizon runtime mapping aligned with automatic scheduled workers,
prospective tool readiness, and schedule-specific access approval. Preserve the
separate protected Objective work-session workflow.
Treat automatic-start eligibility as TeamLead-managed through bounded runtime
settings; retain operator control of explicit denies, the kill switch and limits.
Keep memory timers on the local MemReviewAgent scheduler and document the offline
upgrade for old TeamArchitect timers. Preserve queued review records; distinguish
them from claimed jobs, saved worker tasks, and pending NATS deliveries.
Do not infer absent delegation boundaries from a request that failed to match.
Keep review-batch continuation, actionable Inbox status and tool-returned workflow
links synchronized with Universal Agents' runtime mapping.

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

Keep abandoned-review guidance aligned with runtime retirement and
InternalImprovementAgent's metadata-only inspection and permission-checked archive
and purge tools. Preserve unknown outcomes, retention, live/saved-worker protection,
and explicit offline retirement; never recommend deleting timers or replaying
expired reviews to bypass upgrade checks.

Keep runtime inspection guidance aligned with paged schedule/review metadata and
bounded exact-ID detail reads. Do not prescribe Python environments for reading
routine inspection results or treat a pending-job page as the complete queue.

Keep task-backlog guidance aligned with the per-agent sections in Settings → Tasks.
Select the affected agent before purging its queue. Distinguish queue purge
from stopping all work, and preserve owner scope, cancellation history and schedules.
Treat a missing control reply as unconfirmed; inspect current state before retrying.
