# GitHub Projects with gh

Use this reference when working with GitHub Projects through `gh project`.

If the runtime only exposes GitHub through `secure_cli`, use
`project.item.list` first for a known Projects v2 owner/number. Use `api.post`
with `path="graphql"` for project discovery, mutations, and query shapes not
covered by item listing, or report the scope/tooling limitation when the token
lacks project access.

```text
secure_cli(
  provider="github",
  action="project.item.list",
  params={"owner": "OWNER", "project_number": 7, "limit": 100},
  reason="List the current items and board fields for Project 7."
)
```

Do not use `secure_cli` `api.get` for Projects v2. REST paths such as
`orgs/OWNER/projects`, `users/OWNER/projects`, and guessed Projects v2 paths are
classic/wrong for this workflow and commonly produce 404s or root-metadata
loops.

## Essentials

- Project read commands need token scope `read:project`; project mutations may
  need broader project scopes. If a read command reports missing
  `read:project`, ask the user to refresh auth through the credential
  collection form with `read:project`; use `gh auth refresh -s read:project`
  only when direct authenticated shell access is available.
- Use `--format json`, not `--json`, with `gh project ...`.
- For agent runtimes on `gh 2.92.0`, use `gh project item-list --query` for
  assigned-task discovery.
- The default list limit is usually 30; pass `--limit` for non-trivial
  projects.
- Issue or PR lifecycle state is separate from project board status.
- Brokered GraphQL calls use `api.post`, not `api.get`:

  ```text
  secure_cli(
    provider="github",
    action="api.post",
    params={
      "path": "graphql",
      "body": {"query": "query { viewer { login } }"}
    },
    reason="Check GitHub GraphQL access for project lookup."
  )
  ```

## Brokered secure_cli GraphQL

Use this section when the agent has `secure_cli` but not direct authenticated
shell access to `gh project`.

First check auth. Projects reads require `read:project`; `repo` and `read:org`
are not enough:

```text
secure_cli(
  provider="github",
  action="auth.status",
  params={},
  reason="Check broker GitHub scopes before Project task discovery."
)
```

If `read:project` is absent or GraphQL returns a project-scope error, stop and
ask the user to refresh broker GitHub auth through the credential collection
form with `read:project`. Do not ask for a token in chat. Do not keep trying
REST project endpoints.

Discover the signed-in login and org owners:

```text
secure_cli(
  provider="github",
  action="api.post",
  params={
    "path": "graphql",
    "body": {
      "query": "query { viewer { login organizations(first: 100) { nodes { login } } } }"
    }
  },
  reason="Discover GitHub project owners visible to the broker account."
)
```

For each owner login from `viewer.login` plus `viewer.organizations.nodes[].login`,
list open Projects v2 boards:

```text
secure_cli(
  provider="github",
  action="api.post",
  params={
    "path": "graphql",
    "body": {
      "query": "query($owner: String!) { organization(login: $owner) { login projectsV2(first: 100) { nodes { number title closed url } } } user(login: $owner) { login projectsV2(first: 100) { nodes { number title closed url } } } }",
      "variables": {"owner": "OWNER_LOGIN"}
    }
  },
  reason="List Projects v2 boards for one visible GitHub owner."
)
```

For each open board, list items and inspect `Status`, assignees, content type,
and URLs:

```text
secure_cli(
  provider="github",
  action="api.post",
  params={
    "path": "graphql",
    "body": {
      "query": "query($owner: String!, $number: Int!) { organization(login: $owner) { projectV2(number: $number) { ...ProjectTaskBoard } } user(login: $owner) { projectV2(number: $number) { ...ProjectTaskBoard } } } fragment ProjectTaskBoard on ProjectV2 { title url items(first: 100) { nodes { id type content { ... on DraftIssue { title body } ... on Issue { title number url state repository { nameWithOwner } assignees(first: 20) { nodes { login } } } ... on PullRequest { title number url state repository { nameWithOwner } assignees(first: 20) { nodes { login } } } } fieldValues(first: 20) { nodes { ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2FieldCommon { name } } } ... on ProjectV2ItemFieldDateValue { date field { ... on ProjectV2FieldCommon { name } } } ... on ProjectV2ItemFieldNumberValue { number field { ... on ProjectV2FieldCommon { name } } } ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2FieldCommon { name } } } ... on ProjectV2ItemFieldIterationValue { title field { ... on ProjectV2FieldCommon { name } } } } } } } }",
      "variables": {"owner": "OWNER_LOGIN", "number": 1}
    }
  },
  reason="Inspect active Kanban board items for one Projects v2 board."
)
```

Treat project items as active tasks when their `Status` field value is not
`Done`/`Closed`/equivalent. If content is a DraftIssue or assignees are empty,
do not filter by `assignee:@me`; the board itself may be the assignment queue.

## Kanban Assigned Tasks

For a Kanban-style GitHub Project board, list the project items, not just repo
issues. `gh issue list --assignee @me` misses project board status and can miss
project-only work.

Find the board owner and project number:

```bash
gh project list --owner "@me" --limit 100 --format json
gh project list --owner my-org --limit 100 --format json
```

`--owner "@me"` means the project is owned by the signed-in GitHub account. For
an org-owned board, pass the org login instead. The owner is visible in the
GitHub Projects URL/header: `github.com/users/LOGIN/projects/N` uses
`--owner LOGIN`, while `github.com/orgs/ORG/projects/N` or an `ORG / Projects`
header uses `--owner ORG`. Do not use `--owner "@me"` for an org board just
because the signed-in agent is a member of that org.

When the user asks for assigned Kanban tasks without naming a board, check
across all visible project owners. Start with the signed-in user plus every org
returned by `gh org list`, then enumerate open projects for each owner:

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

For each returned `(owner, project number)` pair, inspect active board items.
Do not hardcode a single owner unless the user named that project owner.

List open issue tasks assigned to the signed-in agent and not in Done:

```bash
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" \
  --query "assignee:@me is:issue is:open -status:Done" \
  --limit 200 --format json
```

If this returns no rows, do not conclude that there are no tasks. First list
the board without the assignee/type filters and inspect the actual item shape:

```bash
gh api user --jq .login

gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" \
  --limit 200 --format json --jq '
    .items[]
    | {
        title,
        status: (.status.name // .status // ""),
        type: (.content.type // .type // ""),
        assignees: ([.content.assignees[]?.login] + [.assignees[]?.login] | unique),
        repo: (.content.repository.nameWithOwner // .content.repository // ""),
        number: (.content.number // null),
        url: (.content.url // .url // "")
      }
  '
```

Then tighten filters one at a time:

```bash
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" --query "-status:Done" --limit 200
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" --query "assignee:@me" --limit 200
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" --query "is:issue is:open" --limit 200
```

Empty filtered output usually means one of these is true: the board uses draft
items rather than linked issues; the item is not assigned at the issue/PR level;
the signed-in `gh` account is not the assignee; or the board uses a different
done column name. For draft-only task boards, omit `assignee:@me` and
`is:issue`, or convert tasks to issues when assignment should drive discovery.
If the board itself is the agent's task queue and the Assignees column is
blank, list active work by Status instead:

```bash
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" \
  --query "-status:Done" \
  --limit 200 --format json --jq '
    .items[]
    | {
        title,
        status: (.status.name // .status // ""),
        type: (.content.type // .type // ""),
        assignees: ([.content.assignees[]?.login] + [.assignees[]?.login] | unique),
        url: (.content.url // .url // "")
      }
  '
```

To check active board items across every visible project in one shell pass:

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
done | while IFS="$(printf '\t')" read -r OWNER PROJECT_NUMBER PROJECT_TITLE PROJECT_URL; do
  echo "### $OWNER project #$PROJECT_NUMBER: $PROJECT_TITLE"
  echo "$PROJECT_URL"
  gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" \
    --query "-status:Done" \
    --limit 200 --format json --jq '
      .items[]
      | {
          title,
          status: (.status.name // .status // ""),
          type: (.content.type // .type // ""),
          assignees: ([.content.assignees[]?.login] + [.assignees[]?.login] | unique),
          url: (.content.url // .url // "")
        }
    '
done
```

For all assigned active items, including PRs and drafts where the project
filter supports them, drop `is:issue`:

```bash
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" \
  --query "assignee:@me -status:Done" \
  --limit 200 --format json
```

For a compact task list with board status:

```bash
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" \
  --query "assignee:@me is:open -status:Done" \
  --limit 200 --format json --jq '
    .items[]
    | {
        title,
        status: (.status.name // .status // ""),
        type: (.content.type // .type // ""),
        repo: (.content.repository.nameWithOwner // .content.repository // ""),
        number: (.content.number // null),
        url: (.content.url // .url // "")
      }
  '
```

Use `status:<column>` or `-status:<column>` to target Kanban columns. Quote
column names with spaces, for example `status:"In Progress"` or
`-status:"Done"`. The `@me` keyword in `assignee:@me` means the signed-in
GitHub account that `gh` is using.

If a specific `gh` build lacks `--query`, fetch JSON and filter locally:

```bash
AGENT_LOGIN="$(gh api user --jq .login)"
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" --limit 200 --format json \
  | jq --arg login "$AGENT_LOGIN" '
      .items[]
      | . as $item
      | ($item.status.name // $item.status // "") as $status
      | select(($status | ascii_downcase) != "done")
      | select(([$item.content.assignees[]?.login] | index($login)) != null)
      | {
          title,
          status: $status,
          type: ($item.content.type // $item.type // ""),
          repo: ($item.content.repository.nameWithOwner // $item.content.repository // ""),
          number: ($item.content.number // null),
          url: ($item.content.url // $item.url // "")
        }
    '
```

## List Projects

```bash
gh project list --owner @me --limit 100
gh project list --owner my-org --limit 100
gh project list --owner my-org --closed --limit 100
```

## View One Project

```bash
gh project view 1 --owner my-org
gh project view 1 --owner my-org --format json
```

Use `--format json` when scripting or when IDs are needed.

## List Fields

```bash
gh project field-list 1 --owner my-org
gh project field-list 1 --owner my-org --format json
```

Use field listing to discover field names, field IDs, single-select options,
and iteration info.

## List Items

Plain table:

```bash
gh project item-list 1 --owner my-org --limit 200
```

JSON:

```bash
gh project item-list 1 --owner my-org --limit 200 --format json
```

## Filter Items

On `gh 2.92.0`, `gh project item-list` supports project filter syntax with
`--query`.

```bash
gh project item-list 1 --owner my-org \
  --query "assignee:@me is:issue is:open" \
  --limit 200

gh project item-list 1 --owner my-org \
  --query "label:bug -status:Done" \
  --limit 200
```

## List Items with Board Status

For Projects, the board-column equivalent is usually `status`.

```bash
gh project item-list 1 --owner my-org --limit 200 --format json --jq '
  .items[]
  | {
      id,
      title,
      type: .content.type,
      repo: .content.repository,
      status: (.status.name // ""),
      url: .content.url
    }
'
```

Notes:

- `status` is the project field value.
- `type` is usually `Issue` or `PullRequest`.
- Project output can also include custom field values such as iteration,
  milestone, dates, numbers, and text fields.

## Compare Lifecycle State and Project Status

Issue or PR lifecycle state is separate from project board status.

Issues:

```bash
gh issue list -R my-org/my-repo --state all \
  --json number,title,state,projectItems \
  --jq '
    .[]
    | {
        number,
        title,
        state,
        projects: [.projectItems[]? | {
          project: .title,
          status: .status.name
        }]
      }
  '
```

Pull requests:

```bash
gh pr list -R my-org/my-repo --state all \
  --json number,title,state,projectItems \
  --jq '
    .[]
    | {
        number,
        title,
        state,
        projects: [.projectItems[]? | {
          project: .title,
          status: .status.name
        }]
      }
  '
```

Use this distinction:

- Issue or PR `state` is `open`, `closed`, or `merged`.
- Project `status` is a board state like `Todo`, `In Progress`, or `Done`.

## Add and Create Items

Add an existing issue or PR:

```bash
gh project item-add 1 --owner my-org \
  --url https://github.com/my-org/my-repo/issues/123
```

Create a draft item:

```bash
gh project item-create 1 --owner my-org \
  --title "Draft task" \
  --body "Investigate API regression"
```

Archive, unarchive, or delete an item:

```bash
gh project item-archive 1 --owner my-org --id PVTI_xxx
gh project item-archive 1 --owner my-org --id PVTI_xxx --undo
gh project item-delete 1 --owner my-org --id PVTI_xxx
```

## Edit Project Item Fields

For non-draft items, `gh project item-edit` needs:

- Item ID
- Project ID
- Field ID
- Value to set

Typical flow:

1. Inspect the project:

   ```bash
   gh project view 1 --owner my-org --format json
   ```

2. Inspect field IDs and options:

   ```bash
   gh project field-list 1 --owner my-org --format json
   ```

3. Inspect item IDs:

   ```bash
   gh project item-list 1 --owner my-org --limit 200 --format json
   ```

4. Update one field:

   ```bash
   gh project item-edit \
     --id PVTI_xxx \
     --project-id PVT_xxx \
     --field-id PVTSSF_xxx \
     --single-select-option-id 47fc9ee4
   ```

Other field types:

- Text: `--text`
- Date: `--date YYYY-MM-DD`
- Number: `--number`
- Iteration: `--iteration-id`
- Clear a field: `--clear`

Only one field value is updated per invocation.

## Linkage and Templates

Use project commands to link or unlink a project to repositories or teams, and
to mark a project as a template. Check `gh project --help` and the specific
subcommand help because required identifiers vary by operation.
