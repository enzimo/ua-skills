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

For a setup-and-post goal, publish a complete `submit_access_workflow` plan before
requesting the first approval. Include account reuse/selection, the existing
capability, any required restart, account verification, the exact post review,
publication, and verification of its returned URL. Follow the visual workflow
section of `runtime-operations-workflows`. Batch independent concrete requests
with `request_access_workflow_approvals`; keep dependent or later-produced
content reviews on that same page. Do not recreate completed setup or ask the
user to drive internal permission commands.

1. Identify the intended X account and the exact post content from the task.
   Publish only within the user's requested scope.
2. Check the existing credential catalog and broker authentication before asking
   for new credentials. Call `secure_cli` with provider `xurl`, action
   `auth.status`, and `params={"credential_binding_id":"<returned binding ID>"}`
   after the reviewed attachment is active. The broker resolves the user-selected
   account; do not guess its catalog key. For a direct catalog workflow, supply
   the actual selected `credential_key` instead. Template names are not account
   identifiers. Verify the returned username matches the intended account.
3. If credentials are missing, render the `xurl_oauth2` credential template using
   `credential_catalog.template.render_request`, then send the structured
   `secure_credential_collection_request` through the gateway. Direct the user
   to the secure form. Never request OAuth values, read token files, run
   `xurl token`, or import tokens through chat or an agent shell.
4. Publish with the exact broker envelope:

   ```json
   {"provider":"xurl","action":"post.create","params":{"credential_binding_id":"<returned binding ID>","text":"The approved post text."},"reason":"Publish the requested update to the selected X account."}
   ```

5. Report the returned post URL and ID as completion evidence. A draft or a
   successful authentication check is not publication.

On `outcome_unknown`, reconcile the account's posts before another publish.
Do not automatically retry; a timeout can follow a successful remote post.
On `account_busy`, wait until the current account operation completes before
checking status again. On auth failure, repair the selected broker credential.
On a permission denial, follow the trusted access-request receipt workflow.

On `credential_binding_credential_mismatch`, check the supplied selector against
the existing approved binding; do not recreate consent just because a guessed
key failed. Use the exact binding ID after attachment. Provisioning status lists
the initial definition separately from later configured attachments, and neither
alone proves activation in the running worker.

Keep credentials in Sealbox or the configured broker store. The broker hydrates
xurl in a private temporary home, persists refreshed OAuth state, and removes
temporary material after use. Installing this skill does not grant posting rights.
Use the broker for authenticated work even though `xurl` is on PATH.

Read [the command reference](references/cli-reference.md) for version and operator
setup details. Media posts, replies, threads, and deletion have no broker action
in this version; do not substitute an arbitrary credentialed shell command.

For a complete communications workflow, include research, draft preparation,
account reuse/selection, attachment, publication review and result verification
in one access plan. TeamLead's routine delegation recommendation excludes
brokered X operations and publishing. Existing routine research authority may be
reused; account binding or attachment never approves a future post. Do not
regenerate completed setup solely because publication needs a later review.
