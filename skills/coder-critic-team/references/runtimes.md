# Runtimes

The protocol is the same everywhere: the lead hands each turn to one worker,
records it with `cct.py`, and hands the next turn to the other. `cct.py` writes
each turn brief to `turns/<role>-brief.md` in the run folder and prints a short
handoff that names it; the lead passes on the handoff, not the brief. Only the
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

Brief every worker with the handoff `cct.py` prints for it, after `cct.py post`
or from `cct.py turn RUN_DIR --for <role>`. A first handoff also names the
role file and the protocol in the run folder. Do not paste the turn brief into
`Agent`, `SendMessage` or `delegate_task`: the worker reads the file. Every
brief names the role file and the protocol at its top, so a worker started
fresh for a turn, or one that replaces another, needs nothing more.

A worker started with `Agent` and `run_in_background: false` answers within
your turn. A worker continued with `SendMessage` answers later: after the
send, finish your turn, and the harness brings you back when the worker
replies. Do not poll or sleep while you wait.

**Checkout.** Give the coder its own branch and worktree. In T3 Code, use the
thread's worktree when it has one. The critic reads the same checkout and
must not write to it. Keep the run folder outside the checkout, for example
next to it in a `cct-runs/` folder.

**GitHub.** The coder pushes the branch and opens the pull request with
`gh pr create --draft`, or pushes to the pull request the brief names and
opens none. The lead files follow-up issues with
`gh issue create`, after checking open issues for an existing one, and marks
the pull request ready with `gh pr ready` once no blocking finding is left.

**Project review.** Invoke the `project-review-process` skill on the pull
request. It chooses and runs its own reviewers.

**Report.**

1. Render both modes: `--mode t3` for the thread and `--mode page` for a file.
   The t3 file is the compact view; the page has every text in full.
2. In T3 Code, call `html_render` once with `path` set to the absolute path of
   the t3 file, a height of 2000 and a short title. Do not pass the HTML
   inline, do not call `html_preview` for a height (the frame fits itself to
   the page), and do not split the report or rebuild parts of it. Do not
   describe the page again in your reply.
3. If `html_render` refuses the file, tell the person and give the page's
   path; show nothing by hand in its place.
4. Reply with three to five lines: the outcome, the pull request link, what
   needs a human decision, and the absolute path of `report.html`.
5. Without T3 Code, give the absolute path of `report.html` and a short
   Markdown summary instead.

**Clean-up.** Clean up a run only after its pull request is merged, usually
later, when the person says so. Leave an unmerged or abandoned run as it is.

1. Confirm the merge: `gh pr view 142 --repo example-owner/relay --json state
   --jq .state` must print `MERGED`.
2. Update the base branch in the main checkout with `git pull --ff-only`
   there, so git sees the merge.
3. Run `cct.py tidy RUN_DIR --merged --worktree`. It removes the coder's
   worktree, the local work branch and the run's working files, and keeps
   `stats.json` and the reports. Leave out `--worktree` when the coder worked
   in the T3 Code thread's own worktree, which belongs to the thread, or in
   the main checkout.
4. Remove nothing else: the report path the person got still opens, and the
   remote branch is left to GitHub or the person.

## Codex

Use Codex's subagent tool (`spawn_agent`, then wait) for workers on Codex
models. For Claude workers from Codex, use the host's cross-provider child
agents when it offers them, such as T3 Code's `delegate_task`; otherwise
tell the person the requested worker model is not available here and ask
which to use. Everything else, the report and the clean-up included, follows
the T3 Code and Claude Code section.

## Universal Agents

Universal Agents routes all work between agents through TeamLead. Workers do
not message each other, and a worker does not keep its model's context from
one turn to the next. Its task keeps its saved work notes. The protocol fits
this: every turn brief carries the critiques and decisions the worker must
answer and points to the plan, and the run folder holds the artifacts (the
briefs, the plan, the diffs, the ledger).

**Scripts.** Load `shell-execution-workflows` before using `shell`. A skill in
`control/skills` runs as
`python3 "${SKILLS_DIR}/coder-critic-team/scripts/cct.py" state RUN_DIR`,
where `RUN_DIR` is the run folder's path. A skill installed through review runs from its installed path, which
`get_runtime_configuration_context()` shows. Pass `work_dir` and an explicit
timeout. Inspect the exit code and the separate output and error; `cct.py`
exits with 2 and prints `Refused:` when it rejects a turn.

In OpenShell mode the sandboxes get no copy of the skill folders, so the
scripts cannot run. Tell the person this skill needs a team without OpenShell
for now, and stop.

**Folders.** Put the run folder in the person's folder, for example
`coder-critic/relay-142/`, never in `scratch/`, which is cleaned up. Keep the
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

**Turns.** Universal Agents stops a task that would wait a sixth time
(`MAX_WAITS_PER_TASK` in `custom_agents/task_wait_limit.py`). A turn counts as
one wait when it delegates a task (a `manager_escalation` included, a
`worker_result` report not), asks the person a question, or sends a
credential form or signup request, however many it sends at once. A
check-back wake that only keeps waiting does not count, and neither does a
pause inside a tool call for a decision in the Inbox (`request_access`,
`apply_change`, `set_up_tools`). The runtime refuses the sixth wait before it
sends anything and fails the task; its requester gets a failure saying that
the task had already waited five times. Each task has its own five:

- The coder's task: one wait for each escalation at the end of a turn.
- Each escalation task: one for the critic task you delegate in it, and one
  for each question you ask the person there.
- Your task for the person's request: one for each coder task you start, each
  critic task you delegate in it yourself, each turn in which the project
  review delegates reviewers, and each question to the person.
- The critic's task does not wait: it answers with its turn.

1. Delegate the coder's task with `delegate_task` and
   `target_named_agent_type="CodeWritingAgent"`. Set
   `check_back_after_minutes` to the brief's stall limit. In the problem
   statement:
   - put the coder's handoff from `cct.py`, which names its turn brief in the
     run folder;
   - say that the role files are in the run folder;
   - give the coder these rules: "At the end of each turn, write your turn
     file and raise a manager_escalation with
     escalation_type=needs_specialist_support that names the run folder and
     your turn file, at most five times in this task. Start each escalation's
     problem statement with 'Escalation N of 5 in this task': N is 1 in a new
     task, and otherwise one more than the number in the answer you just
     received. When the answer to escalation 5 of 5 arrives, finish your task
     with a task_response that names the run folder, without starting that
     turn, unless it is your pr turn. Finish your task after your pr turn
     too. If an escalation comes back failed, finish your task and say so."
2. At the end of each turn, the coder writes its turn file and raises a
   `manager_escalation` with `escalation_type="needs_specialist_support"`.
   The escalation reaches you as a task of its own, so its problem statement
   must give its number and name the run folder and the turn file. The coder
   then waits for the answer.
3. Record the coder's turn. When the critic is next, delegate a new critic
   task with the critic's handoff and its role file and protocol paths in the
   problem statement, and the same `check_back_after_minutes`.
4. When the critic's `task_response` arrives, record its turn. Answer the
   coder's escalation task with a `task_response` that starts with "Answer to
   escalation N of 5", with the escalation's number, followed by the coder's
   next handoff unchanged. When the coder is next again at once, answer
   without delegating.
5. You wake when delegated tasks end or the check-back time passes. A missing
   reply shows a transport or responsiveness problem; it does not mean the
   work finished.
6. When a coder task ends, record `turns/coder-next.json` if it is there
   (its pr turn, or a turn the coder finished its task on). Then continue
   from `cct.py state RUN_DIR`: start a new coder task with the handoff from
   `cct.py turn RUN_DIR --for coder`, after a critic task when the critic is
   next. The fix round starts a new coder task with the coder's fix handoff
   the same way.

**How many turns fit.** A coder task holds five coder turns, six when the
sixth is its pr turn. A run needs about `max_checkpoints` plus five coder
turns before its pull request. Plan the five waits of your request before
you start:

- Waits 1 and 2: two coder tasks, so ten coder turns before the pull
  request, eleven when the eleventh is the pr turn. That fits
  `max_checkpoints` up to six.
- Waits 3 and 4: the project review, with its reviewers in one delegating
  turn and at most one separate critic round. Re-check fixes by reading them
  and running the tests, not by delegating again.
- Wait 5: the fix round's coder task. Keep it until the project review shows
  no blocking finding.

A question to the person or a recovery takes one of these. When the waits
left do not cover what the run still needs, stop when a coder task has ended
and none is running: record a `note`, say in your `task_response` where the
run stands, and continue from `cct.py state RUN_DIR` in the person's next
request. For a longer run, split the brief into runs that fit, or run the
project review in a request of its own.

**When the limit stops a task.** Nothing more is sent, and the task's
requester gets the failure. Its turn file is still in the run folder:
`cct.py post` deletes a `-next.json` file only once it records it, so a
`turns/coder-next.json` or `turns/critic-next.json` there is a turn not yet
recorded. Record it with the actor its name gives, then continue from
`cct.py state RUN_DIR` in a new task: a critic task first when the critic is
next, then a new coder task. A stopped coder task that left a turn costs your
request up to two waits this way. When your own request's task was stopped, do this
in the person's next request. The commits stay.

A worker reads only the brief `cct.py` wrote for it, its role file, the
protocol and the files that brief names. Never pass a turn by telling a worker
to read another worker's files. When a worker's task cannot read the run
folder, put the output of `cct.py turn RUN_DIR --for <role> --full` in the
delegation instead of the handoff.

**Access.** Check `list_my_access`. The coder's pull request needs `cli:github`.
Ask with `request_access(tool_id="cli:github", level="write", reason=...,
hand_on=true)`. For a missing GitHub sign-in or account link, call
`set_up_tools` at once rather than asking the person first.

**GitHub.** `gh` is blocked in shell. Load `secure-credential-workflows`, then:

- When the brief names an existing pull request, push to it and open none.
- Otherwise open a draft pull request with `secure_cli(provider="github",
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

**Report.** Publish the report as a hosted page from its statistics file:

1. Run `cct.py stats RUN_DIR`. It writes `stats.json` into the run folder.
2. Call `publish_single_page_site(site_kind="report", site_spec_path=...)`
   with the path of that file, and leave `site_spec_json` empty. A relative
   path starts in the person's folder, for example
   `site_spec_path="coder-critic/relay-142/stats.json"`; the file may be up
   to 2 MB. Never pass the statistics as text in `site_spec_json`: a run's
   statistics are too large to pass that way.
3. Give the person the returned `site_url` exactly as returned. Anyone with
   the link can open the page, so give it only to people who may see the
   work.
4. To publish again in place after `cct.py stats` rewrote the file, pass the
   same `site_spec_path` with `update_site_id` set to the `site_id` the first
   call returned. Do not edit `stats.json`.
5. Put the three-to-five-line summary with the link in your final
   `task_response`.

A refused path (`file_not_found` or a folder-rule refusal) usually means the
path does not name the run folder's `stats.json`; correct it once. Send the
report as a file instead when the team's Universal Agents cannot publish it:
the tool's description names no `report` kind or no `site_spec_path`, or the
call fails with an input error naming `site_kind`, `site_spec_path` or
`site_spec_json` (a release without them), with `failure_reason`
`invalid_site_kind`, or with `invalid_report_stats` (its copy of the report
renderer is older than this skill). Then:

1. Render `--mode page` into the run folder.
2. Send it with `notify_user(message=..., attachments=[{"path":
   "coder-critic/relay-142/report.html", "filename": "report.html",
   "content_type": "text/html", "caption": "Work report"}])`.
3. Tell the person why there is no page, and that they can open the report
   from Web Chat's files, where the preview blocks scripts. The report needs
   none.
4. Put the three-to-five-line summary in your final `task_response`.

The person's attachment is a copy in their `scratch/sent` folder, which
scratch clean-up removes later, so the run folder's `report.html` is the
lasting copy.

**Clean-up.** Clean up only after the pull request is merged, usually in a
later request when the person asks. Leave an unmerged or abandoned run as it
is.

1. Confirm the merge with `secure_cli(provider="github", action="pr.view",
   params={"repo": "example-owner/relay", "pr_number": 142}, reason=...)`.
   Its `state` must be `MERGED`.
2. Run `cct.py tidy RUN_DIR --merged`. The checkout is a clone, a
   repository's main checkout, which `--worktree` never removes.
3. Remove the clone with `rm -r` in `shell` only when
   `git status --porcelain` and `git log --branches --not --remotes
   --oneline` both print nothing in it, so no change or commit exists only
   there. Otherwise tell the person what is left in it.
4. Remove the run folder when the report is a hosted page: the page keeps its
   own copy in `sites/` of the person's folder and stays. After the
   attachment fallback, keep the run folder, or first tell the person where
   its `report.html` is.
