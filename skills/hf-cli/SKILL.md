---
name: hf-cli
description: Searches Hugging Face models and datasets, downloads Hub files, and uploads explicit file content through Universal Agents' broker. Use for Hugging Face Hub workflows, not generic model training or unrelated file transfers.
---

# Hugging Face Hub

Use `shell-execution-workflows` for CLI execution and
`secure-credential-workflows` for broker credentials and authorization.
The executable is `hf`, supplied by `huggingface_hub`; do not install a package
named `hf-cli` or run a runtime self-update.

For a reviewed capability attachment, use its returned
`credential_binding_id` in place of `credential_key` in every broker request.
The broker resolves the selected account internally. Supply exactly one
selector; template names are not necessarily catalog keys. A credential-key
mismatch does not by itself justify repeating credential consent.

1. Choose the requested repository, type, operation, and artifact. Search public
   models or datasets with bounded results. Use `--json` for structured output:

   ```bash
   HF_HUB_DISABLE_IMPLICIT_TOKEN=1 HF_HUB_DISABLE_UPDATE_CHECK=1 hf models ls --search bert --limit 3 --json
   ```

2. Inspect file metadata and sizes before downloading. Pin a commit revision
   when reproducibility matters, select specific files, and use a workspace
   destination. Do not execute downloaded model code as part of a download.
3. For private/gated downloads or uploads, select an existing catalog credential
   and check `secure_cli` provider `huggingface`, action `auth.status`, with
   `params={"credential_key":"huggingface_api_token"}`. Verify the returned account.
   On missing credentials, use the `huggingface_api_token` collection template
   and gateway secure form. Never ask for token values in chat or hydrate them
   into the agent's shell, workspace, Git credentials, or skills.
4. Use `file.download` with `credential_key`, `repo_id`, `repo_type`, `filename`,
   and a full 40-character commit `revision`. Decode the returned `content_base64`
   into the intended workspace artifact. The broker accepts one literal file
   up to 1 MiB and returns its revision and size.
5. Use `file.upload` with the same fields plus explicit `content_base64`. The
   revision must equal the current `main` commit in an existing repository.
   The broker writes only that file using the HF SDK's atomic parent-commit
   check, because the upstream `hf upload` CLI also creates missing repositories
   and branches. Report the returned commit ID and URL.

When a broker result has `failure_stage=credential_resolution`, read its
`error_code`, `required_field`, `action_owner`, and `next_action`. If
`provider_operation_attempted=false`, explain that the tool operation was not
attempted; do not claim the external service rejected authentication. A missing
field means the selected credential is incompatible (X needs secret
`oauth_json`; Hugging Face needs secret `api_token`). Ask the owner to select or
create the matching credential through the secure workflow. Source configuration,
read failures, or empty values go to TeamLead for diagnosis and operator help
when needed. Correct only issues within existing authority; these diagnostics
grant no permission. Preserve completed setup, never guess credential keys or
repeat consent/attachment/restart indiscriminately, and do not retry the unchanged
request when `retry_safe=false`. Never request or transmit secrets through chat.

On revision conflict, inspect the remote change and reassess the requested upload.
On an unknown write outcome, reconcile remote commits before another write.
On credential denial, follow the exact trusted access-request workflow.
For larger private artifacts, paid Jobs, endpoints, hardware changes, repository
creation/deletion, or remote execution, report the unsupported broker operation;
do not work around it with credentialed arbitrary shell commands.

Read [the CLI reference](references/cli-reference.md) for public command examples
and the pinned version. Keep caches for public artifacts separate from any
private material. Installing the CLI or skill grants no additional authority.
