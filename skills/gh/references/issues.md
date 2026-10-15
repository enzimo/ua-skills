# GitHub Issues with gh

Use this reference for issue state changes and operations that are not covered
by the broker's allowlisted `issue.*` actions.

## Brokered secure_cli Issue Closure

In a `secure_cli` runtime, `github.api.post` always runs
`gh api --method POST`. It accepts only `path` and optional JSON `body`.
Parameters such as `method`, `field`, `args`, and `endpoint` are not supported.

Do not try to close an issue with:

```text
action="api.post"
params={
  "path": "repos/OWNER/REPO/issues/123",
  "method": "PATCH",
  "field": {"state": "closed"}
}
```

That does not PATCH the issue. Use GraphQL instead.

1. Fetch the issue node id:

```text
secure_cli(
  provider="github",
  action="api.get",
  params={"path": "repos/OWNER/REPO/issues/123"},
  reason="Fetch issue node id before closing it through GraphQL."
)
```

Use the returned `json.node_id` as `ISSUE_NODE_ID`.

2. Close the issue with `closeIssue`:

```text
secure_cli(
  provider="github",
  action="api.post",
  params={
    "path": "graphql",
    "body": {
      "query": "mutation($id: ID!) { closeIssue(input: {issueId: $id, stateReason: COMPLETED}) { issue { number state stateReason closedAt url } } }",
      "variables": {"id": "ISSUE_NODE_ID"}
    }
  },
  reason="Close the completed GitHub issue."
)
```

3. Verify with the broker issue view action:

```text
secure_cli(
  provider="github",
  action="issue.view",
  params={"repo": "OWNER/REPO", "number": 123},
  reason="Verify the issue is closed."
)
```

If GraphQL reports missing permissions, stop and ask the user to refresh broker
GitHub auth through the credential collection form with scopes that can write to
the repository. Do not ask for a token in chat. Do not fall back to shell
`gh issue close` when shell access is blocked by policy.

## Direct gh Issue Closure

When direct authenticated shell `gh` is available, close issues with the native
command:

```bash
gh issue close 123 -R OWNER/REPO --reason completed
gh issue view 123 -R OWNER/REPO --json number,state,stateReason,url
```

Prefer `--reason completed` for finished work and `--reason "not planned"` when
the issue should be closed without being completed.
