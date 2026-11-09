# Runtimes

The protocol is the same everywhere: the lead hands each turn to one worker,
records it with `cct.py`, and hands the next turn brief to the other. Only the
way workers start, receive turns and reach GitHub differs. Read the section
for the runtime you are in.

Recognise the runtime from what you can see:

- **T3 Code:** the `html_render` tool is available.
- **Universal Agents:** the prompt has a `Your Team ID:` line, and you act
  through structured actions such as `delegate_task`.
- **Claude Code or Codex without T3:** neither of the above.

## T3 Code and Claude Code

**Workers.** Start the coder and the critic as subagents, one at a time and in
the foreground:

- When a worker runs on your own provider with no settings beyond yours, use
  the `Agent` tool with the worker's `model` and `effort` (by default `opus`
  and `xhigh`) and `run_in_background: false`. Continue the same worker with
  `SendMessage`, so it keeps its context between turns.
- When a worker needs another provider, model or effort than yours, follow the
  host's rules for child agents. In T3 Code that is `delegate_task` with the
  model and `effort` in `target.options`, after `orchestrator_capabilities`.
  Start a new child for each of that worker's turns; the turn brief carries
  what it needs.

Brief a new worker with: its role (`roles/coder.md` or `roles/critic.md` in
the run folder), the protocol (`roles/protocol.md`), and the output of
`cct.py turn RUN_DIR --for <role>`. Brief a continued worker with the turn
brief only.

**Checkout.** Give the coder its own branch and worktree. In T3 Code, use the
thread's worktree when it has one. The critic reads the same checkout and
must not write to it. Keep the run folder outside the checkout, for example
next to it in a `cct-runs/` folder.

**GitHub.** The coder pushes the branch and opens the pull request with
`gh pr create --draft`. The lead files follow-up issues with
`gh issue create`, after checking open issues for an existing one, and marks
the pull request ready with `gh pr ready` once no blocking finding is left.

**Project review.** Invoke the `project-review-process` skill on the pull
request. It chooses and runs its own reviewers.

**Report.**

1. Render both modes: `--mode t3` for the thread and `--mode page` for a file.
2. In T3 Code, call `html_preview` with the t3 HTML to get its
   `contentHeight`, then `html_render` with that height and a short title. If
   the preview is unavailable, pass a height of 2000. Do not describe the page
   again in your reply.
3. Reply with three to five lines: the outcome, the pull request link, what
   needs a human decision, and the absolute path of `report.html`.
4. Without T3 Code, give the absolute path of `report.html` and a short
   Markdown summary instead.

## Codex

Use Codex's subagent tool (`spawn_agent`, then wait) for workers on Codex
models. For Claude workers from Codex, use the host's cross-provider child
agents when it offers them, such as T3 Code's `delegate_task`; otherwise
tell the person the requested worker model is not available here and ask
which to use. Everything else follows the T3 Code and Claude Code section.

## Universal Agents

Universal Agents routes all work between agents through TeamLead. Workers do
not message each other, and a worker does not keep its model's context from
one turn to the next. Its task keeps its saved work notes. The protocol fits
this: every turn brief carries the critiques and decisions the worker must
answer, and the run folder holds only artifacts (the plan, the diffs, the
ledger).

**Scripts.** Load `shell-execution-workflows` before using `shell`. A skill in
`control/skills` runs as
`python3 "${SKILLS_DIR}/coder-critic-team/scripts/cct.py" state <run folder>`.
A skill installed through review runs from its installed path, which
`get_runtime_configuration_context()` shows. Pass `work_dir` and an explicit
timeout. Inspect the exit code and the separate output and error; `cct.py`
exits with 2 and prints `Refused:` when it rejects a turn.

In OpenShell mode the sandboxes get no copy of the skill folders, so the
scripts cannot run. Tell the person this skill needs a team without OpenShell
for now, and stop.

**Folders.** Put the run folder in the person's folder, for example
`coder-critic/<run name>/`, never in `scratch/`, which is cleaned up. Keep the
checkout in the task's folders (a public repository can be cloned into
`agents/`).

**Worker types.** Use the team's `CodeWritingAgent` for the coder; it works
with `code:shell` and `github`. For the critic, use a reviewing specialist the
team already has (`get_available_agent_types()`). If there is none, propose
one:

1. Call `use_tools(tool_ids=["fn:capabilities"])`.
2. Call `specialist_definitions(action="plan", agent_type="CodeCritic",
   display_name="Code Critic", role=..., description=..., prompt=...,
   default_tools=[...], reason=...)`. Set `prompt` to the text of
   `roles/critic.md` and the protocol, and list one to eight tool ids in
   `default_tools`.
3. Call `apply_change` with the returned change ID straight away. It asks the
   person in the Inbox and returns once they decide.

A generated specialist cannot have `code:shell` as a default tool. The critic
reads the diffs `cct.py` writes into the run folder, so it needs no shell. If
it should run tests, ask with `request_access(tool_id="code:shell",
level=..., reason=..., hand_on=true)` so you can hand it on to the critic's
tasks.

**Models.** The model is a setting of each agent type:

1. Read the current values with
   `get_runtime_configuration_context(agent_types=["CodeWritingAgent", ...])`.
   The catalog of settings is `list_runtime_settings_options()`, after
   `use_tools(tool_ids=["fn:runtime_settings"])`.
2. With the person's agreement, stage a change with
   `plan_runtime_setting_change(path="current_agent.llm.model_id", value=...,
   target_scope="agent_type", target_agent_type="CodeWritingAgent",
   reason=...)` and apply it with `apply_change`.

The change affects every task of that agent type, not only this run. Some
providers ignore `current_agent.llm.reasoning_effort`, the native Anthropic
and Bedrock providers among them. A person's own saved model
(`/auth model me`) replaces every agent type's model for their work. Record in
the brief the model and effort that will actually apply; omit `effort` when
none applies.

**Turns.**

1. Delegate the coder's task with `delegate_task` and
   `target_named_agent_type="CodeWritingAgent"`. Set
   `check_back_after_minutes` to the brief's stall limit. In the problem
   statement:
   - put the coder's turn brief;
   - say that the role files are in the run folder;
   - say that at the end of every turn until its `pr` turn is recorded, the
     coder raises the escalation in step 2 instead of finishing its task.
2. At the end of each turn, the coder writes its turn file and raises a
   `manager_escalation` with `escalation_type="needs_specialist_support"`.
   The escalation reaches you as a task of its own, so its problem statement
   must name the run folder and the turn file. The coder then waits for the
   answer.
3. Record the coder's turn. Delegate a new critic task with the critic's turn
   brief in the problem statement and the same `check_back_after_minutes`.
4. When the critic's `task_response` arrives, record its turn. Answer the
   coder's escalation task with a `task_response` whose answer is the coder's
   next turn brief.
5. You wake when delegated tasks end or the check-back time passes. A missing
   reply shows a transport or responsiveness problem; it does not mean the
   work finished.
6. The coder's task ends with its `pr` turn. For the fix round, delegate a new
   coder task with the coder's fix turn brief, following the same pattern.

Never pass a turn by telling a worker to read another worker's files. Put what
it must answer in the delegation; the turn brief does this.

**Access.** Check `list_my_access`. The coder's pull request needs `cli:github`.
Ask with `request_access(tool_id="cli:github", level="write", reason=...,
hand_on=true)`. For a missing GitHub sign-in or account link, call
`set_up_tools` at once rather than asking the person first.

**GitHub.** `gh` is blocked in shell. Load `secure-credential-workflows`, then:

- Open a draft pull request with `secure_cli(provider="github",
  action="gh.exec", params={"argv": ["pr", "create", "--draft", "--repo",
  ..., "--head", ..., "--base", ..., "--title", ..., "--body", ...]},
  reason=...)`. Without a draft, use `action="pr.create"` with
  `params={"repo", "title", "body", "head", "base"}`.
- Mark it ready later with `gh.exec` and `["pr", "ready", ...]`.
- Before filing a follow-up, check `action="issue.list"`, then use
  `action="issue.create"`.

The branch must be on GitHub first. If the team has no way for agents to push
a branch, stop before the pull request. Keep the reviewed branch and a
`git format-patch` series in the run folder, then close the run as `blocked`
with a note. Tell the person what is ready and what is missing. Do not copy a
token into a remote URL or the shell environment.

**Project review.** Run `project-review-process` when the team has it
(`skills(skill_name="project-review-process")`). It is not bundled with
Universal Agents. If it is missing, record
`{"type": "review_result", "ran": false, "reason": "project-review-process is not installed for this team"}`.
Do not replace it with an ad hoc review without saying so. Tell the person the
skill can be added as a team skill.

**Report.** Universal Agents' `publish_single_page_site` renders only its own
theme, so it cannot show this design. Instead:

1. Render `--mode page` into the run folder.
2. Send it with `notify_user(message=..., attachments=[{"path":
   "<run folder>/report.html", "filename": "report.html", "content_type":
   "text/html", "caption": "Work report"}])`.
3. Tell the person they can open it from Web Chat's files, where the preview
   blocks scripts. The report needs none.
4. Put the three-to-five-line summary in your final `task_response`.
