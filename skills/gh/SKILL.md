---
name: gh
description: Use GitHub from a terminal-only environment through raw gh or the brokered secure_cli GitHub action surface. Trigger when Codex needs to inspect or manage GitHub repositories, issues, pull requests, Actions runs and workflows, releases, Projects, secrets, variables, search, aliases, extensions, or GitHub REST/GraphQL API calls.
---

# GitHub CLI

Use this skill for GitHub work when browser access is unavailable or unwanted.
Prefer terminal output, JSON, and scripting-friendly commands.

## Brokered Runtime First

Some Crew runtimes expose GitHub only through the structured `secure_cli` tool.
When `secure_cli` is available, use it for credentialed GitHub operations
instead of raw shell `gh` commands. `secure_cli` is not a generic argv
passthrough: call one allowlisted action with named `params`.

Universal Agents blocks `gh` at the shell policy boundary before RTK planning,
including nested shell attempts. The shared `shell-execution-workflows` skill
documents this policy boundary. Do not retry with an `rtk` prefix, `rtk proxy`,
or `sh -c`. Use `secure_cli` and
`secure-credential-workflows`; use the raw examples below only in a separate
trusted shell where direct authenticated `gh` is explicitly allowed.

Example shape:

```text
secure_cli(
  provider="github",
  action="repo.view",
  params={"repo": "owner/repo"},
  reason="Inspect repository metadata for the user's request."
)
```

Supported GitHub broker actions:

| Goal | Action | Params |
| --- | --- | --- |
| Check auth | `auth.status` | optional `hostname` |
| Logout broker `gh` | `auth.logout` | optional `hostname`, `user` |
| Login from credential manager | `auth.login.credential` | `credential_provider`, `item_id` or `item_name`, optional `field_ref`, `hostname`, `vault`, `folder` |
| View repo | `repo.view` | `repo` |
| List issues in one repo | `issue.list` | `repo`, optional `state`, `limit` |
| View issue | `issue.view` | `repo`, `number` |
| Create issue | `issue.create` | `repo`, `title`, optional `body`, `labels` |
| Comment on issue | `issue.comment` | `repo`, `number`, `body` |
| List PRs in one repo | `pr.list` | `repo`, optional `state`, `limit` |
| View PR | `pr.view` | `repo`, `number` |
| Create PR | `pr.create` | `repo`, `title`, optional `body`, `head`, `base` |
| Comment on PR | `pr.comment` | `repo`, `number`, `body` |
| List workflow runs | `workflow.run.list` | `repo`, optional `workflow`, `limit` |
| List Projects v2 items | `project.item.list` | `owner`, `number` or `project_number`, optional `limit` |
| Raw REST GET | `api.get` | `path` |
| Raw REST/GraphQL POST only | `api.post` | `path`, optional JSON `body` |

For `api.get`, put the complete GitHub API path, including any query string, in
`params.path`. Do not invent `endpoint`, `query`, `args`, or full URL params.
Use no leading host:

```text
params={"path": "user"}
params={"path": "user/repos?per_page=100"}
params={"path": "search/issues?q=assignee%3A%40me+is%3Aopen+is%3Aissue&per_page=100"}
params={"path": "repos/owner/repo/issues?state=open&per_page=100"}
```

For GraphQL through the broker, use `api.post` with `path="graphql"` and a JSON
body:

```text
params={
  "path": "graphql",
  "body": {"query": "query { viewer { login } }"}
}
```

`api.post` always runs `gh api --method POST`; it is not a generic method
override. Do not pass `method`, `field`, `args`, or `endpoint` params. For
REST operations that require PATCH/PUT/DELETE, do not keep retrying `api.post`
with `method: "PATCH"`; use an allowlisted action, direct `gh` if available,
or a GraphQL mutation through `api.post path=graphql`.

Common broker workflows:

- Assigned issues across accessible repos: use `api.get` with
  `search/issues?q=assignee%3A%40me+is%3Aopen+is%3Aissue&per_page=100`.
- Repo-local issues or PRs: use `issue.list` or `pr.list`; these actions always
  require `repo`.
- Closing an issue in brokered mode: there is no `issue.close` action and
  `api.post` cannot PATCH `repos/OWNER/REPO/issues/NUMBER`. Fetch the issue's
  GraphQL node id with `api.get path="repos/OWNER/REPO/issues/NUMBER"`, then
  call `closeIssue` through `api.post path=graphql` with
  `body.query='mutation($id: ID!) { closeIssue(input: {issueId: $id, stateReason: COMPLETED}) { issue { number state stateReason } } }'`
  and `body.variables={"id":"NODE_ID"}`. Verify afterward with `issue.view`.
- GitHub Projects and Kanban boards: use `project.item.list` first when the
  project owner and number are known. For discovery, mutations, or queries not
  covered by that read action, Projects v2 are GraphQL-backed; do not probe REST paths such as
  `orgs/OWNER/projects`, `users/OWNER/projects`, or guessed Projects v2
  endpoints with `api.get`. Use `api.post` with `path="graphql"` as shown in
  [references/projects.md](references/projects.md). If `auth.status` or a
  GraphQL error shows the broker token lacks `read:project`, stop and ask the
  user to refresh broker GitHub auth with `read:project` instead of trying
  alternate endpoints. If a Projects query shape is wrong or incomplete, fix
  the GraphQL selection set; do not switch to shell `gh project ...` in a
  brokered runtime.

Credential handling:

- Check broker auth first with `auth.status` when `secure_cli` is available.
- Use `auth.login.credential` when an existing credential-manager item is
  available by ID/name, or after a metadata search identifies the right item.
- Use direct `gh auth status` only when raw authenticated shell access is
  available and broker policy allows it.
- Do not ask the user to paste GitHub tokens, passwords, recovery codes, or
  credential-manager secrets into chat.
- If new or refreshed GitHub credentials are required, direct the user to the
  credential collection form with `/auth github web` or `/auth github`; include
  needed scopes such as `read:project` in the instruction.

Failure discipline:

- If `issue.list` errors because `repo` is missing, switch to `api.get`
  `search/issues` for cross-repo searches; do not retry `issue.list` without a
  repo.
- If `api.get` says `path` is missing, retry once with only
  `params={"path": "..."}`.
- If `api.get` returns the GitHub API root metadata (`current_user_url`,
  `repository_url`, etc.), the path was effectively `/`; retry once with the
  intended endpoint fully inside `params.path`. If it still returns root
  metadata, stop and explain the tool-shape limitation instead of cycling
  through endpoint/path permutations.
- If the broker returns `error_code=auth_required`, ask the user to run
  the credential collection form with `/auth github web` or `/auth github`.

Use the raw `gh` guidance below only when direct shell access to authenticated
`gh` is available.

## Ground Rules

- Do not use `--web`.
- Do not use `gh browse`.
- Prefer terminal-native commands such as `view`, `list`, `status`, `checks`,
  `watch`, `download`, and `api`.
- Many commands operate on the current repo; otherwise pass `-R OWNER/REPO`.
- For automation, use `--json` on normal commands when available.
- For `gh project ...`, use `--format json` instead of `--json`.
- Use `--jq` to filter command output where possible.
- Use `gh api` or `gh api graphql` when higher-level commands are not enough.

Useful defaults:

```bash
export GH_REPO=owner/repo
export GH_PROMPT_DISABLED=1
```

## Discovery

Start with help and authentication checks when command shape or auth state is
unclear:

```bash
gh help
gh <command> --help
gh help formatting
gh auth status
```

Most `gh` commands use `--json`; `gh project ...` uses `--format json`.

## Repository Management

Use `gh repo` for repository inventory, metadata, cloning, creation, forks, and
settings.

```bash
gh repo list my-org --limit 100
gh repo view my-org/my-repo
gh repo clone my-org/my-repo
gh repo fork cli/cli --clone=false
```

## Issues

Use `gh issue` to create, list, view, edit, comment on, close, reopen, and
inspect issues relevant to the current user.

```bash
gh issue list -R my-org/my-repo --state open --assignee @me
gh issue view 123 -R my-org/my-repo --comments
gh issue create -R my-org/my-repo --title "Bug" --body "Details"
gh issue edit 123 -R my-org/my-repo --add-label bug
gh issue status
```

Useful JSON fields include `number`, `title`, `state`, `assignees`, `labels`,
`milestone`, `projectItems`, and `url`.

For closing issues or other state changes not covered by the broker's
allowlisted `issue.*` actions, read [references/issues.md](references/issues.md).

## Pull Requests

Use `gh pr` to list, view, create, checkout, review, inspect checks, merge,
close, reopen, and inspect PRs relevant to the current user.

```bash
gh pr list -R my-org/my-repo --state open --author @me
gh pr view 456 -R my-org/my-repo --comments
gh pr checkout 456 -R my-org/my-repo
gh pr checks 456 -R my-org/my-repo
gh pr review 456 -R my-org/my-repo --approve
gh pr merge 456 -R my-org/my-repo --squash --delete-branch
gh pr status
```

Useful JSON fields include `number`, `title`, `state`, `reviewDecision`,
`statusCheckRollup`, `mergeable`, `projectItems`, and `url`.

## GitHub Actions

Use `gh workflow` to list, view, run, enable, and disable workflows. Use
`gh run` to list runs, view logs, watch runs, rerun, cancel, and download logs
or artifacts.

```bash
gh workflow list -R my-org/my-repo
gh workflow run ci.yml -R my-org/my-repo
gh run list -R my-org/my-repo --limit 20
gh run view 123456789 -R my-org/my-repo --log
gh run watch 123456789 -R my-org/my-repo
```

## Releases

Use `gh release` to list, view, create, upload assets, and download assets.

```bash
gh release list -R my-org/my-repo
gh release view v1.2.3 -R my-org/my-repo
gh release create v1.2.4 ./dist/* -R my-org/my-repo --notes "Release notes"
gh release download v1.2.3 -R my-org/my-repo
```

## Projects

Use `gh project` for GitHub Projects. Project commands require token scope
`read:project` for reads and broader project scopes for writes; if they fail
unexpectedly, check token scopes.

Common starting points:

```bash
gh project list --owner my-org --limit 100
gh project view 1 --owner my-org
gh project field-list 1 --owner my-org
gh project item-list 1 --owner my-org --limit 200
```

For a Kanban-style personal task board, the key command is
`gh project item-list <project-number> --owner <project-owner>`. On the target
agent `gh 2.92.0` runtime, list tasks assigned to the signed-in agent with
project filter syntax through `--query`:

```bash
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" \
  --query "assignee:@me is:open -status:Done" \
  --limit 200 --format json
```

Choose `--owner` from the project URL/header. Use `--owner "@me"` only for a
user-owned project under the signed-in account. For an org board, use the org
login as `--owner`. To discover tasks without knowing the board owner up front,
check projects owned by both the signed-in user and every visible org:

```bash
AGENT_LOGIN="$(gh api user --jq .login)"
OWNERS="$(
  {
    printf '%s\n' "$AGENT_LOGIN"
    gh org list --limit 100
  } | sort -u
)"

printf '%s\n' "$OWNERS" | while read -r OWNER; do
  gh project list --owner "$OWNER" --limit 100 --format json \
    --jq ".projects[] | select(.closed == false) | [\"$OWNER\", .number, .title, .url] | @tsv"
done
```

If the board itself is the agent's queue and the Assignees column is blank,
filter by project Status instead of `assignee:@me`:

```bash
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" \
  --query "-status:Done" \
  --limit 200 --format json
```

If another `gh` build does not show `--query` in `gh project item-list --help`,
fetch JSON and filter locally instead; see [references/projects.md](references/projects.md).

For detailed project item filtering, status inspection, and field editing,
read [references/projects.md](references/projects.md).

## Search

Use `gh search` for GitHub-wide lookup across repositories, issues, pull
requests, code, and commits when repo-local lists are not enough.

## Secrets and Variables

Use `gh secret ...` and `gh variable ...` to manage repo, org, and environment
configuration for CI and automation.

## Other Built-Ins

Use these built-ins when relevant:

- `gh gist` for gists
- `gh label` for labels
- `gh ssh-key` for SSH keys
- `gh ruleset` for repository and org rulesets
- `gh alias` for shortcuts
- `gh extension` for installed add-ons

## Raw API Access

Use `gh api` when a top-level command is missing a feature.

```bash
gh api repos/{owner}/{repo}
gh api repos/{owner}/{repo}/issues
gh api graphql -f query='
  query {
    viewer {
      login
    }
  }
'
```

## Best Practices

- Be explicit about repo context outside a repository:

  ```bash
  gh issue list -R owner/repo
  gh pr list -R owner/repo
  gh run list -R owner/repo
  ```

- Prefer JSON for automation:

  ```bash
  gh repo list my-org --json nameWithOwner,visibility --jq '.[]'
  gh issue list -R my-org/my-repo --json number,title,state --jq '.[]'
  gh pr view 123 -R my-org/my-repo --json title,state,url
  ```

- Inspect supported JSON fields by checking command help or invoking `--json`
  without field names.
- Remember that many list commands default to 30 items; pass `--limit` for
  `repo list`, `issue list`, `pr list`, `run list`, `project list`,
  `project item-list`, and `project field-list`.

## Minimal Cheat Sheet

```bash
gh auth status
gh repo list my-org --limit 100
gh repo view my-org/my-repo

gh issue list -R my-org/my-repo --state open
gh issue view 123 -R my-org/my-repo --comments

gh pr list -R my-org/my-repo --state open
gh pr view 456 -R my-org/my-repo --comments
gh pr checks 456 -R my-org/my-repo

gh workflow list -R my-org/my-repo
gh run list -R my-org/my-repo --limit 20
gh run view 123456789 -R my-org/my-repo --log

gh release list -R my-org/my-repo
gh release view v1.2.3 -R my-org/my-repo

gh project list --owner my-org --limit 100
gh project view 1 --owner my-org
gh project field-list 1 --owner my-org
gh project item-list 1 --owner my-org --limit 200
gh project item-list 1 --owner my-org --limit 200 --format json
```
