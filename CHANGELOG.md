# Changelog

All notable changes to this project are documented in this file. This project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- `long-horizon-plan-execution` no longer tells the agent to stop duplicate
  tasks with `control_task_queue`. That tool now pauses, resumes or stops only
  tasks of the request the agent is working on; for a duplicate or any other
  request, the agent reports the task ID and tells the person to ask in that
  request's own thread or to stop it with `/stop task <task_id>`.
- `user-onboarding-guide` saves tour progress with the `record_digest` of the
  listed progress fact. Universal Agents refuses an agent's memory replace or
  delete without the version of the fact it read, so a delayed change cannot
  overwrite a newer one or reach a different fact that took over its number.
  If the replace is refused with `changed_since_read`, the guide lists again.
- Personal-details checks now come from the shared project template:
  `scripts/check_personal_details.py` also checks commit identities, commit
  messages and every line in history; Git hooks in `.githooks/` run it before
  commits and pushes; the **Personal details** workflow runs it in CI. The rules
  moved from `README.md` to `CONTRIBUTING.md`, and
  `docs/personal-details-cleanup.md` covers what to do when a detail was already
  pushed. The allowlist includes the reviewed GitHub web-merge author identity.
- `long-horizon-plan-execution` no longer tells the team lead to use research
  runs, a plan tree, a work ledger or a limit on parallel Objective work. Those
  tools never shipped in Universal Agents, so the instructions named tools the
  team lead does not have. The skill now matches the copy Universal Agents
  ships, and its runtime mapping was checked against current code:
  `authorize_scheduled_job_access` gives access to the schedule itself; during
  a scheduled job's run a person decides each access request; `request_access`
  takes a tool and a level but no operation; workflow steps are reported with
  `update_access_workflow`; and the team lead reaches the team's Objectives and
  those of the person it works for.
- `xurl` tells the agent to call `request_access` with the `tool_id` (normally
  `cli:x`) and `level` a refusal names, without an operation: access is to a
  whole tool at a level.
- `long-horizon-plan-execution` describes how Objective status changes now
  behave in Universal Agents: `objectives(action="update_status")` applies the
  same change as the person's Runtime Controls, so pausing or closing an
  Objective also pauses its bounded work sessions and resuming turns back on
  only what a control paused, while system-managed schedules stay as they are
  and are named in `lifecycle_warnings`; the tool refuses `deleting` and
  `deleted`, which come only from the person's own deletion; each status offers
  only some Runtime Controls, and repeating the control that set the current
  status retries what did not finish; and a task that ends while its Objective
  is paused or being deleted leaves it that way.
- `long-horizon-plan-execution` tells the team lead to change an Objective from
  what it last read: `objectives(action="get")`, `list` and `create_objective`
  return the Objective's `version`, and `update_progress` and `update_status`
  need it as `expected_version`. A `changed_since_read` refusal means another
  request changed its definition or success criteria, so the team lead reads
  it again and decides on what it says now. Status, progress and runtime links
  do not change the version. This needs a Universal Agents
  release where the Objective tools take a version.

## [0.2.0] - 2026-10-15

The repository was recreated without its earlier history. The `0.1.0` tag and
its release archives are retired; this is the first release of the new
repository.

### Changed

- `user-onboarding-guide` greets with made-up names in its example first
  greeting, and `gog` uses `you@example.com` as its sample account. A new test
  fails when a tracked file contains a real-looking email address, phone number
  or personal home folder path; `README.md` ("Personal Details") lists what stays
  out of the repository and which placeholders to use.

- `gog` explains paging: gog returns one page of results, and when the JSON
  includes `nextPageToken` the agent repeats the command with
  `--page <nextPageToken>` until no token comes back. A check that must see
  every match is complete only after the last page. This needs a Universal
  Agents release where the broker no longer hides paging bookmarks.

- The long-horizon runtime mapping names Universal Agents' Objective action tools,
  `objective_work_sessions` and `objective_work_profiles`, which replaced the nine
  work-session and profile functions (`suggest_objective_work_session` and the rest).
  `propose_objective_work_profile` keeps its name.

- `crawl4ai` and the repository notes name Universal Agents' `mcp_connections`
  tool (`mcp_connections(action="list"|"propose")`), which replaced
  `list_mcp_connections` and `propose_mcp_connection`.

- `user-onboarding-guide` saves its progress with Universal Agents' `memory`
  tool (`memory(action="list"|"replace"|"create", bank="usermem")`), which
  replaced `list_usermem`, `replace_usermem` and `create_usermem`.

- `xurl`, `crawl4ai`, `skill-creator` and the long-horizon runtime mapping say
  which of TeamLead's tool groups load on request in Universal Agents
  (objectives, solution variations, access workflows and proposals, MCP and
  specialists, team skills) and that it loads them
  with `use_tools(tool_ids=[...])` before calling their functions. Plan
  execution and recovery stay in its tool list, and objective work sessions
  already have the objectives tools.

- `xurl`, `hf-cli`, `gog`, `crawl4ai`, `brave-search` and
  `user-onboarding-guide` follow Universal Agents' per-team sharing choice for
  each service that takes both a person's own and the team's account. Shared:
  the team's account serves anyone who has not linked their own. Private: the
  team's account is never used, not even for work that serves no person, and
  `/link <tool> team` is refused. `/accounts` shows the choices, and owners and
  administrators change them with `/accounts share <tool>` and
  `/accounts private <tool>`. `xurl` says that X starts private, so the team's
  X account is the fallback only after `/accounts share cli:x`, and tells agents
  never to request the team's X account while X is private. `hf-cli`,
  `brave-search` and the Crawl4AI MCP connection (`crawl4ai`) say that the
  team's account is used only while shared (the default); `crawl4ai` also says
  that the Crawl4AI web tool (`http:crawl4ai`) takes only the team's token and
  is always shared. `gog` says that Google Workspace is always private.
  `user-onboarding-guide` explains `/accounts` to administrators and that people
  added from now on may use the team's model keys unless an administrator sends
  `/accounts private model` (`--own-keys` and `/user team-keys` still decide
  per person). It also tells administrators that a new person sees their
  first-time setup (their own model when needed, their own account for each
  private service someone in the team already uses) on their first message,
  and that `/setup` repeats it.

- The long-horizon runtime mapping and the repository guidance follow
  Universal Agents' "access follows the work": workers keep no access of their
  own, each task gets what TeamLead may hand on, TeamLead asks with
  `request_access` and `hand_on=true`, and scheduled jobs a worker runs hold
  their own access. TeamLead keeps its access in its scheduled runs, and
  workers in TeamLead's schedules and the runtime's timers get what it hands
  on. `give_access` is gone, and `request_access` takes no `operation`.

- `gh`, `gog`, `xurl` and the long-horizon runtime mapping use `/link <tool id>`,
  the one command people now use for every tool's account: `/link cli:github`
  (`web`, `web-all`), `/link cli:google` (`json_token`) and `/link cli:x`.
  `/auth github ...` and `/auth google [web|json_token|credentials]` are gone;
  a person's own Google sign-in app is pasted on the `/link cli:google` page,
  and `/auth google team_client` stays for administrators. `xurl` says that X
  uses the person's own X browser sign-in first, then the team's linked X
  account (`/link cli:x team`, administrators only); people no longer link a
  personal X account, and a call with neither fails with `x_account_missing`.
  Its command reference explains the team's X app (`/auth x team_client`).

- `brave-search` and `crawl4ai` say that the Brave Search and Crawl4AI keys
  are linked accounts in the credential store (`http:brave-search`,
  `http:crawl4ai`, `mcp:crawl4ai`), which the broker adds to each request,
  never environment variables; a missing key is fixed with `/link <tool> team`.
  The shipped Crawl4AI connection uses a credential slot, and the shell `curl`
  examples are only for use outside Universal Agents.

- `gog`, `gh`, `hf-cli` and `xurl` say that each person's own sign-in or
  account link is used only for that person's work and that no tool token comes
  from environment variables. `gog` explains the team's Google sign-in app
  (`/auth google team_client`, administrators only), a person's own app, and the
  new `google_oauth_client_missing`, `google_keyring_password_missing` and
  `person_required` results; `hf-cli` adds the `model.info` broker action.

- `crawl4ai` follows the Universal Agents MCP grants model: the server is the
  tool `mcp:crawl4ai`, installed on one Inbox card (an access proposal) and
  used while the agent holds access for the person it works for; full access
  covers every Crawl4AI tool. `plan_mcp_connection_activation`,
  `load_mcp_connection_tools` and per-agent-type attachment are gone.

- `crawl4ai` tells agents to read `load_status` from `find_tools` and
  `list_mcp_connections` when its tools are missing: the server is not
  answering (retried for a limited time, then administrators are told) or the
  broker refused.

- `single-page-site` says that a published page is written into `sites/` of
  the person's folder and served only while it matches what the tool wrote, so
  agents change a page by publishing again with `update_site_id`, not by
  editing the file. Anyone with a page link can open it; its chat works only
  for the person it was made for, signed in to Web Chat.

- `markitdown` says that the Universal Agents code sandbox keeps commands off
  the network unless the agent holds full access to shell commands, so the
  first `uvx` download of MarkItDown may need `request_access` with
  `tool_id='code:shell'` and `level='full'`. Inputs and outputs may also be in
  a folder the agent was given, such as a registered data folder.

- `xurl`, `hf-cli`, `crawl4ai`, `brave-search`, and the long-horizon runtime
  mapping use Universal Agents account links instead of credential bindings:
  broker requests carry no credential key or binding id, and a missing account
  is fixed by linking a stored credential to the tool (`cli:x`,
  `cli:huggingface`, `mcp:<connection>`, or an operator-defined `http:*` web
  API tool).
- `xurl`, `crawl4ai`, and the long-horizon runtime mapping describe only the
  current Universal Agents access model: a refused call names the tool and
  level to ask for with `request_access`, TeamLead hands access on with
  `give_access`, and a person decides the rest in the Inbox. Mentions of
  delegation envelopes, routine delegation recommendations, Cedar resources,
  and human interaction records are removed.

## [0.1.0] - 2026-08-13

### Added

- Initial curated collection of Universal Agents skills.
- Deterministic per-skill release archives and SHA-256 checksums.
- Automated validation and GitHub release publishing for version tags.

[Unreleased]: https://github.com/enzimo/ua-skills/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/enzimo/ua-skills/releases/tag/v0.2.0
