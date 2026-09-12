---
name: xurl
description: Publishes text posts and checks account identity on X using the xurl CLI through Universal Agents' credential broker. Use for X posting requests, not web search or other social networks.
---

# X posting

Use `secure-credential-workflows` for credential collection and binding, and
`shell-execution-workflows` for ordinary command execution.

For a specialist that needs X access, select the existing trusted
`builtin:x_posting` capability. It permits only brokered `auth.status` and
`post.create`. Follow `runtime-operations-workflows` to prepare its exact
credential binding, collect the user's account selection/consent, and attach
that capability through the normal review flow. Keep invocation approval
separate. Do not request a delegation-envelope change to register X tools and
do not ask the user to write slash commands. If the registry lacks this id,
report the runtime version/registry gap; do not invent a registration request.

1. Identify the intended X account and the exact post content from the task.
   Publish only within the user's requested scope.
2. Check the existing credential catalog and broker authentication before asking
   for new credentials. Call `secure_cli` with provider `xurl`, action
   `auth.status`, and `params={"credential_key":"xurl_oauth2"}`. Substitute the
   selected catalog key. Verify the returned username matches the intended account.
3. If credentials are missing, render the `xurl_oauth2` credential template using
   `credential_catalog.template.render_request`, then send the structured
   `secure_credential_collection_request` through the gateway. Direct the user
   to the secure form. Never request OAuth values, read token files, run
   `xurl token`, or import tokens through chat or an agent shell.
4. Publish with the exact broker envelope:

   ```json
   {"provider":"xurl","action":"post.create","params":{"credential_key":"xurl_oauth2","text":"The approved post text."},"reason":"Publish the requested update to the selected X account."}
   ```

5. Report the returned post URL and ID as completion evidence. A draft or a
   successful authentication check is not publication.

On `outcome_unknown`, reconcile the account's posts before another publish.
Do not automatically retry; a timeout can follow a successful remote post.
On `account_busy`, wait until the current account operation completes before
checking status again. On auth failure, repair the selected broker credential.
On a permission denial, follow the trusted access-request receipt workflow.

Keep credentials in Sealbox or the configured broker store. The broker hydrates
xurl in a private temporary home, persists refreshed OAuth state, and removes
temporary material after use. Installing this skill does not grant posting rights.
Use the broker for authenticated work even though `xurl` is on PATH.

Read [the command reference](references/cli-reference.md) for version and operator
setup details. Media posts, replies, threads, and deletion have no broker action
in this version; do not substitute an arbitrary credentialed shell command.
