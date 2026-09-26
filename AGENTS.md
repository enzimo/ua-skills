# Agent Instructions (`AGENTS.md`)

This file guides AI agents when operating within the `ua-skills` repository.

Keep Crawl4AI setup aligned with the Universal Agents MCP model: an installed
server is the tool `mcp:crawl4ai`, and agents see its tools while they hold
access to it for the person they work for. A pending server is installed on
one Inbox card (`propose_access_change` with `mcp_servers`, or
`propose_mcp_connection` for a new one) or by an administrator in the MCP
controls; full access to `mcp:crawl4ai` covers every Crawl4AI tool. A
connection whose operator configuration declares credential slots uses the
stored token linked to `mcp:crawl4ai` (the person's own link first, then the
team's). Never treat an OpenShell lease as MCP authority or copy a token into
configuration.

## Intent is king
- Make sure you execute to intent rather than to your written plan. If you find during implementation of the plan that it is drifting from the intent, stop and adjust your approach. Executing to intent is **paramount**. We must make sure to verify that the intent is clear and whenever there are deviations in code or plan, to communicate with the user to clarify intent and to change the plan + code to execute to intent.

## Repository Purpose

This repository stores and manages Universal Agents (UA) Agent Skills under the `skills/` directory.

## Available Skills

The canonical list of available skills is maintained in `README.md` under "Available Skills". Update that table when adding, removing, or renaming skills under `skills/`.
The catalog includes `user-onboarding-guide` for Universal Agents first-run opt-in capability tours.
The catalog includes `single-page-site` for generated articles, comparisons,
procedural how-tos, and browser-local interactive apps. Keep it aligned with
how Universal Agents serves pages: from `sites/` of the person's folder, only
while they match what the tool published, with the page chat limited to the
person the page was made for.
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
keeping it waiting for the next timer tick. Before telling the owner to approve
something in the Inbox, confirm that a real access request or staged change is
waiting there.
Keep completion-failure recovery explicit: preserve checkpoints, verify the saved
Objective policy/schedule link and resume a blocked Objective after repair.
Keep selective solution variation bounded and discretionary. Treat candidate
evaluations and selections as advisory records rather than workspace isolation,
effect authority, integration, or final verification.
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
   - Use `skills/skill-creator` to scope skills with concrete examples, bootstrap their files, validate and package them, and iterate from observed results.
   - Author skills as procedural anchors for capable agents. Define applicability, completion evidence, ordered decisions, checkpoints, failure recovery, and invalidating assumptions where they stabilize execution.
   - Keep names and descriptions concise and discriminating. Test materially revised skills with similar distractors and out-of-scope near-misses when routing quality matters.
   - Create `scripts/`, `references/`, and `assets/` only for a concrete execution role. Request resource directories explicitly from the initializer and load references only when the active procedure needs them.
   - Treat `quick_validate.py` as a structural gate, not proof of behavioral quality. Compare observable outcomes for substantial revisions and preserve success or failure labels when learning from trajectories.
   - Skill instructions must be written in the **imperative/infinitive form**.
   - Frontmatter name must be `hyphen-case`, and description must be in third-person without `<` or `>` characters.
   - For skills that use credentials, instruct agents to check hydrated CLI/runtime auth, environment variables, secret-file mounts, or credential stores before requesting new credentials. Never instruct agents to request secrets in chat; direct users to the runtime credential collection form when new credentials are required.
   - Keep `skills/gog/SKILL.md` aligned with installed `gog` command help, the broker's canonical auth methods, Google's External Testing 7-day refresh-token rule, and the `secure_cli` provider/action/params request format, especially Gmail search/send params, `gog.exec` argv nesting, decoded-body behavior, and attachment-download behavior.
     Preserve the distinction between a renamed account's provider-reported email
     and a different account selected at consent; neither permits bypassing the
     account check.
   - For skills that run commands in Universal Agents, route shared process behavior through the runtime `shell-execution-workflows` skill. Keep domain skills focused on their own command flags and policy caveats; do not duplicate or contradict the shared RTK, timeout, working-directory, result, or broker-boundary contract.
   - For user-facing authorization updates, name the concrete server, tool,
     agent, credential, or action. On denial or failure, state what did not
     happen, why, and the next useful step. Keep attach, invoke, grant, lease,
     consumed, and revoke in technical details.

4. **Versioning and Releases:**
   - Use Semantic Versioning and store the canonical version in `VERSION`.
   - Update `CHANGELOG.md` for each release.
   - Tag releases as `v<version>` with an exact match to `VERSION`.
   - Run the release tests and artifact build before pushing a release tag.
   - Publish deterministic per-skill ZIP archives and `SHA256SUMS` through the GitHub Actions release workflow.

The `xurl` and `hf-cli` skills pair with Universal Agents bundled templates.
Keep their broker request formats and versioned command references synchronized with
`../universal-agents`, using `python -m scripts.sync_hub_cli_skills --check`
from that checkout. Authenticated operations use the broker; do not instruct
agents to copy Sealbox values into their own shell environments.

Use the existing `builtin:x_posting` capability for reviewed specialist X access.
Keep its X account (the person's own sign-in with `/link cli:x`, else the
team's account link), attachment, and access to `cli:x` separate; ask for
missing X access with `request_access`. In every skill, people set up a tool's
account with `/link <tool id>` (GitHub, Google and X sign-ins included);
`/auth` keeps only status, the team's sign-in apps (`team_client`) and the
password managers.

Keep the long-horizon runtime mapping aligned with automatic scheduled workers,
prospective tool readiness, and schedule-specific access approval. Preserve the
separate protected Objective work-session workflow.
Treat automatic-start eligibility as TeamLead-managed through bounded runtime
settings; retain operator control of explicit denies, the kill switch and limits.
Keep memory timers on the local MemReviewAgent scheduler and document the offline
upgrade for old TeamArchitect timers. Preserve queued review records; distinguish
them from claimed jobs, saved worker tasks, and pending NATS deliveries.
Check `list_my_access` before handing access on with `give_access` or asking
for it with `request_access`.
Keep review-batch continuation, actionable Inbox status and tool-returned workflow
links synchronized with Universal Agents' runtime mapping.

Keep the guidance on handing access to workers and correcting unfinished review
steps aligned with the runtime mapping. Preserve saved Inbox reviews across workflow-link errors
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
