# Changelog

All notable changes to this project are documented in this file. This project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

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

[Unreleased]: https://github.com/enzimo/ua-skills/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/enzimo/ua-skills/releases/tag/v0.1.0
