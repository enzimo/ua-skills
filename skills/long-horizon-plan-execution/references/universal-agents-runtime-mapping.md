# Universal Agents Runtime Mapping

## Apply Runtime Primitives

Map the OODA operating model to Universal Agents without inventing identifiers,
side channels, or authority:

| OODA concept | Universal Agents mechanism |
| --- | --- |
| Team lead | `TeamArchitect` |
| Bounded execution | Structured `Task` |
| Isolated long research | Durable `ResearchRun` |
| Human decision | `TaskQuery` through the manager |
| Durable outcome | Manager-owned `ObjectiveRecord` |
| Living strategy | Manager-owned `PlanRecord` |
| Bounded plan execution | `activate_plan_execution` |
| Multi-session bounded execution | Opt-in `ObjectiveWorkPolicy` and `ObjectiveWorkSession` |
| Cross-session handoff | `ObjectiveWorkCheckpoint` |
| Current state | Execution digest |
| Chronology | Task history |
| Liveness and pressure | `AgentStatus`, `TaskStatus`, `get_runtime_pressure` |
| Delegation | Structured `delegate_task` action |
| Recovery event | `record_plan_action` |
| Fresh recovery context | `start_isolated_recovery` |
| Optional solution comparison | Solution-variation tools |
| Durable wait | Schedules and heartbeat items |
| Lesson candidate | `AfterActionReport` |

Keep plan, objective, digest, and history state local to the manager or agent
that owns it. Send all inter-agent work through structured transport. Include
the required task-local context in every delegation.

A successful `TaskStatus` refresh confirms liveness, not progress or approval.
The runtime spaces status probes using the last successful probe; do not create
replacement tasks just because a worker is waiting. A delegated task waits in
its worker type's queue until a free worker takes it; the runtime starts
workers and does not probe or time out a task that is still waiting, so do not
start workers or delegate it again. A missing reply is a
transport or responsiveness observation, not evidence that the task completed.
For a missing sign-in, account link or team sign-in app, TeamLead calls
`set_up_tools` at once, without asking the person first. Trusted code asks for
missing access, opens every page in the person's chat (routed to the
configured gateway even when a worker needed the account), shows one workflow
page for two or more things (each page shows on its step, and trusted code
marks the step from the page result), and pauses the task until the pages end
instead of treating tool approval as a set-up account. An expired page is
offered again by itself, up to three pages per tool and kind; a closed page or
a denial ends the setup, and the call returns per tool whether it is ready.

A published access workflow belongs to its source Task and is a view over its
access requests. Staging its changes or closing the local execution plan does
not finish that workflow. Follow `runtime-operations-workflows`, and read every
request's current status with `get_access_workflow` when the same task resumes.
Approval permits only the exact change; it does not prove execution. Complete steps after verifying
their results, or record a concrete failure and recovery action. If an older
source task has already ended, inspect its workflow from the follow-up task and,
when the user requests continuation, plan only the remaining work. Keep completed
results and check uncertain external effects before another attempt.

Use the `review_url` returned by workflow submission or inspection for live
progress links. Never use a skill documentation address as the workflow link.
Ask for independent staged changes together with
`request_access_workflow_approvals` (one pause for all of them), then apply each
approved change with `apply_change`, and check every outcome before reporting.
When the lead itself lacks a tool a worker needs, it calls `request_access` with
`hand_on=true`; the worker's task then gets it from the lead's access when it
needs it (access follows the work: workers keep no access of their own). Never ask again for anything a
person denied: the denial closes its workflow step.

## Use Hierarchical Objective Plans and the Work Ledger

For an Objective, treat the current `PlanHierarchySnapshotV1` as the
authoritative living strategy. Its `PlanHorizonRecordV1` entries separate the
committed near-term horizon from forecast horizons. Its nested
`PlanNodeRecordV1` entries represent subplans, milestones, discovery, delivery,
and verification branches. Use `PlanRevisionRecordV1` to record why strategy
changed and the next committed planning action.

Activate this skill before `create_objective`,
`update_objective_plan_hierarchy`, or `enqueue_objective_work_item`. Objective
creation persists a partial two-horizon Plan. Later horizons may remain
forecast, but material work requires an accepted or provisional goal contract,
a committed horizon, an actionable or bounded discovery node, evidence and
progress definitions, stop and replan triggers, review cadences, and the
activated skill's content digest.

Use `get_objective_plan_hierarchy` to inspect the current Plan revision and
ledger. Use `update_objective_plan_hierarchy` for one compare-and-set revision.
Do not fabricate owner, Objective, Plan, revision, or skill-digest fields; the
runtime derives them from current trusted state and the current activation.

Manager custody does not grant access to other users' Objectives or Plans.
Planning tools act for the canonical user bound to the active Task, including
trusted periodic and result-review Tasks. If that identity is missing or the
Objective belongs to another user or team, do not retry with invented owner,
task, Plan, or manager identifiers.

Standalone Plans retain the canonical owner of their trusted root Task. A task
identifier also does not authorize reading its digest or promoting it to an
Objective. On an Objective/Plan version conflict, reload current canonical state
and reconsider the intended update; do not force an older whole record over it.
Persistence and recovery errors are failures, not confirmation that a milestone
or result was saved. Preserve useful evidence and report the failed operation.

The Plan tree is not an execution queue. Put intended bounded work in
`ObjectiveWorkItemRecordV1` through `enqueue_objective_work_item`. The ledger
may contain more work than current runtime capacity. Preserve semantic
idempotency keys, dependencies, horizon order, stable queue rank, readiness,
and source Plan revision. A work item may represent research, a specialist
Task, an execution-control job or run, a managed service, a schedule, a durable
wait, Plan review, result integration, or cancellation.

Requested placement is intent, not authority. A worker or model cannot exempt
itself from local accounting by naming a remote placement. Trusted admission
assigns the execution class and opaque runtime reference. Objective-local work
holds one of two default slots from admission until a fenced terminal result,
cancellation acknowledgement, or lease expiry. Keep additional ready work in
the ledger. Remote runtimes, execution control, external services, and passive
waits enforce their own capacity and do not consume Objective-local slots. A
remote-eligible item consumes a local slot when it falls back to local work.

Do not widen the two-slot local limit informally. TeamArchitect may stage an
inert `propose_objective_parallelism` record only after identifying independent
streams, cost/time impact, and shared-resource risk. Tell the authenticated
Objective owner to use `/accept objective-parallelism <objective_id>
<proposal_id> <proposal_digest>`. Conversational confirmation is not authority.
The accepted cap automatically returns to two at the next Plan revision, which
requires a fresh proposal for any later increase.

Promote long evidence work with `create_research_run`. Objective-linked
research must use a Research work item that has passed Objective admission;
never supply only an Objective id. Copy only the bounded
question, current Objective/Plan slice, accepted evidence and procedures,
budgets, and stop conditions into the immutable
ResearchRun context. The isolated worker gets a fresh Strands instance and no
origin conversation or shared-memory channel. It returns a structured terminal
capsule to TeamArchitect first. TeamArchitect validates provenance and fences,
then decides whether the evidence changes the Plan, completes a node, cancels
or replaces other ResearchRuns, or makes new work ready. Research, ordinary
Tasks, execution-control work, managed services, schedules, and durable waits
may coexist in the ledger; their placement and authority boundaries remain
distinct.

The run's worker starts with its role's standard tools, and its tool list
follows the access its task has for the person the Objective works for: the
task gets the tools the question needs from what the lead may hand on, when it
first needs them. If the worker asks with `request_access`, treat the wait as a
checkpoint: the task pauses until a person decides, and a grant is usable on
the worker's next step without a restart. An Objective-linked
wait releases its local slot and must reacquire it before resuming. New web
API tools, data folders, account links and MCP servers stay on their reviewed
paths (`propose_access_change`, MCP installation); a worker request never
grants them.

Worker terminal results enter the Objective integration queue. TeamArchitect
reviews the result and current Plan revision before integration, replanning,
cancellation, replacement work, milestone notification, or presentation to the
originating user thread. Workers never write the originating conversation or
mutate the Plan directly. The runtime queues a durable `research_presentation`
Task for this review; if admission is full, the terminal event remains pending
instead of being marked delivered.

One Research work item binds one ResearchRun. Retrying creation for that item
does not request a second parallel run. Put a genuinely separate question or
periodic occurrence in a new work item. Artifact inspection is limited to the
active Task or ResearchRun directory; carry accepted evidence through the
context manifest instead of reading another run's raw filesystem paths.

Resuming after an access wait preserves the previous terminal capsule as a disk-backed
continuation reference. Review and reuse its partial findings without treating
them as verified merely because they survived a restart. Exhausted attempts
and queued cancellation produce coordinator observations for TeamArchitect
review, not fabricated worker results. The review Task and terminal receipt
commit together; duplicate transport delivery is not a reason to create a
second review or send a second user answer.

## Select Task, Plan, or Objective

- Keep a simple request as a `Task`.
- Add a `Plan` for durable checkpoints, unknowns, recovery, or multiple bounded
  stages.
- Promote recurring, standing, long-horizon, or separately tracked outcomes
  to an `Objective`.
- Use `activate_plan_execution` for complex work that should execute in fresh
  bounded manager steps.

Treat these lifecycles independently after promotion:

- Keep the `Objective` as durable outcome ownership until its own completion
  policy reaches a terminal disposition.
- Keep the Objective's current `Plan` as durable strategy across replaceable
  execution Tasks. Do not infer Plan completion or failure from a Task's
  terminal state.
- Let an Objective-linked `Task` complete when its bounded execution is done,
  even when Plan work remains.
- After a Task failure, call `start_objective_task` to create a fresh Task that
  hydrates and resumes the same active Plan.
- Call `update_execution_plan_status` when the Plan attempt itself becomes
  completed, failed, cancelled, or abandoned. A later `start_objective_task`
  creates a new Plan attempt under the same non-terminal Objective when the
  prior current Plan is terminal.
- Treat the Task that created an Objective as provenance only unless it is also
  explicitly part of the Objective-owned task lineage. Its later failure must
  not change the successfully created Objective or Plan.

Supply semantic titles, objectives, rationale, evidence needs, and recovery
intent. Leave runtime-owned task, plan, step, conversation, correlation, and
routing identifiers to the runtime.

## Use solution variation only when it helps

`TeamArchitect` may use `start_solution_variation` when several materially
different approaches are plausible and a bounded comparison could change the
decision. It may then record candidate hypotheses, agent-authored evaluations,
and one advisory selection; inspect the current comparison during resumption;
and close it after integration and ordinary verification. It should skip this
path when a direct solution is already clear.

These records are a manager-owned sidecar. They neither create Tasks nor add a
new transport primitive. They also do not isolate a workspace, apply an
artifact, authorize an effect, change Task, Plan, or Objective status, or turn
agent-authored references into runtime-verified evidence. Competing branches
may proceed concurrently only when they are read-only or already have a real
independent mutation boundary. Otherwise compare before editing and use one
sequential integration owner.

## Use Objective work sessions when available

The runtime may load Objective work-session profiles by default, but availability
does not time-box any Objective. When an Objective is likely to need multiple
execution windows, call `suggest_objective_work_session`; the suggestion is
inert and reports the available profile catalog and whether custom proposals
are enabled. Do not create an ordinary schedule as a substitute for an
Objective work-session policy.

Use this negotiation sequence:

1. Call `list_objective_work_profiles` and compare the operator profiles and
   the authenticated user's private installed profiles with the Objective's
   cadence, work duration, checkpoint reserve, model-turn, token, and tool-call
   needs.
2. If an existing profile fits, summarize its exact bounds and call
   `enable_objective_work_sessions` only in the authenticated user request that
   explicitly accepts those bounds.
3. If none fits, discuss the bounds first, then call
   `propose_objective_work_profile`. Use `scope="objective"` for a one-time
   profile bound to one active Objective, or `scope="reusable"` for a private
   profile the user can install for future Objectives. A proposal is inert.
4. Show the proposal's exact profile, scope, expiry, proposal id, and digest.
   Call `apply_objective_work_profile_proposal` with that same id and digest
   only after the authenticated user explicitly accepts it. Never treat
   `confirmed=true` as a substitute for the user's actual acceptance.
5. Applying a one-time proposal enables its target Objective. Applying a
   reusable proposal only installs the owner-scoped profile; select it later
   with `enable_objective_work_sessions` for each Objective that should use it.

Discuss the complete profile rather than changing one limit in isolation:

- cadence and its time zone (`owner` by default: the Objective owner's time zone)
- active duration and wall-clock checkpoint reserve
- total turns and checkpoint-reserved turns
- total input-plus-output tokens and checkpoint-reserved tokens
- total tool calls and checkpoint-reserved checkpoint tool calls

All budget values are cumulative across one work session. None reset per model
turn. Active duration is the total wall-clock session window; turns count model
cycles; tokens accumulate input plus output across cycles; and tool calls count
all calls across cycles. Each checkpoint reserve is a subset of its session
total.

For an accepted Objective policy, `tool_calls` is the authoritative total for
that work session; the ordinary `agent.max_tool_calls_per_task` limit does not
silently shrink it. `checkpoint_reserve_tool_calls` is only retry headroom for
the checkpoint-only `record_objective_work_checkpoint` pass. It does not add
material-work tool capacity, and the built-in operator limit allows at most
five reserved attempts.

Explain the material-work allowance after reserves. When a run reaches a
`limit_*` boundary, inspect `get_objective_work_status` for the latest input,
output, total, cache, turn, tool, wall-time, overshoot, evidence-delta, and
`tuning_signals` data. Treat those signals as observations, not authority.
Diagnose the binding dimension and context-to-output ratio, then discuss a
complete revised profile with explicit headroom for Strands' safe-boundary
soft-cap overshoot. Never auto-apply a wider token, time, turn, cadence, or tool
budget; use a fresh exact proposal and acceptance.

Objective, Plan, policy, and checkpoint ownership survives runtime replacement.
An owner id shaped like `manager_scope:<team>:TeamArchitect` names the current
same-team manager role, not an expired TeamArchitect process. Continue the
Objective after restart; do not hand work back to the former runtime id. Never
use this rule to cross a team, named role, or authenticated-user boundary.

Authenticated users retain direct control of their durable work independently
of a particular TeamArchitect process. The user can open **Runtime Controls**
from Web Chat or use `/objectives` to review authoritative Objective state and
the current Plan subgoals. Available lifecycle commands are `/pause objective
<id>`, `/resume objective <id>`, `/stop objective <id>`, `/abandon objective
<id>`, and `/delete objective <id>`. Pause prevents future managed runs; stop
also cancels current Objective work at a safe boundary; abandon retains a
terminal record; delete disables linked future work, stops active work, and
creates a recoverable tombstone while retaining Plans, evidence, checkpoints,
and audit history. User controls resolve canonical-user ownership and may adopt
legacy same-team TeamArchitect custody before acting. Never attempt to bypass,
forge, or weaken these authenticated controls.

Runtime Controls also exposes owner-scoped schedules and authorized MCP
lifecycle actions. Treat a user pause, disable, detach, stop, remove, abandon,
or delete as a change to actual runtime state: re-observe before continuing,
reconcile in-flight effects, and do not recreate the resource or schedule unless
the user explicitly asks. Agents may recommend a control, but they must not
impersonate the browser user or an operator to apply one.

Use `export_objective_work_profile_yaml` to render a deterministic schema-v2
policy layer for an agreed configured, installed, or Objective-scoped profile.
Rendering is read-only. Saving requires explicit user confirmation and writes
only under `control/objective_execution_profiles/`; it does not activate the layer.
Tell the operator to append its path relative to `control/` after the base layer in
`workspace.objective_execution_paths` and restart the manager. Later layers
replace same-named profiles and may adjust strict policy sections. Missing
files are warned and skipped; malformed files stop startup. Never edit the main
config, reorder policy authority, or restart through this export tool.

The operator-owned policy file bounds custom cadence and budgets. Do not edit
that file, fabricate a digest, broaden a proposal, or bypass a state-drift
rejection. Create a fresh proposal if the target policy or reusable profile
changed before acceptance. Removing an installed profile removes it from
future selection but does not mutate policies already snapshotted onto
Objectives. Reconfiguring an Objective updates its existing protected schedule
in place.

Activate this skill through the normal protected `skills` tool during every new
session before material work.

At resume, load the canonical Objective, current Plan, latest checkpoint, and
recent evidence. Revalidate authority, procedures, stale evidence, and in-flight
effects before acting. Respect the runtime's safe boundary: stop starting new
subgoals and call `record_objective_work_checkpoint` while checkpoint reserve
remains. Record Observe, Orient, Decide, Act, Objective health, evidence delta,
completed and next subgoals, blockers, artifacts, and in-flight effects. Do not
turn activity counts into an invented completion percentage.

Finish each bounded session with a terminal `task_response` after saving its
checkpoint. Keep unfinished work in the durable Objective and Plan for the next
session; do not keep the current Task waiting for a future timer tick. Report a
blocked session honestly without claiming that its remaining subgoals succeeded.
Use a fresh interactive conversation for a repair that requires human input when
the background Task has no external reply route. Before telling the owner to
approve something in the Inbox, check that a real access request or staged
change is waiting there.

If session completion reports a policy, schedule or owner verification failure,
inspect the saved work policy, its linked schedule and the saved checkpoint.
Do not recreate a valid schedule merely because gateway delivery metadata is
missing. The failed Task releases its slot, but normal failure review can mark
its Objective blocked. After verifying or repairing the link, explicitly resume
the existing Objective if needed; do not erase checkpoints or bypass ownership.

The runtime withholds the configured turn, token, and checkpoint-tool reserves
from material work. If a work invocation reaches a safe boundary without a
checkpoint, it performs a narrow checkpoint-only invocation. A deterministic
degraded checkpoint is the fallback when that pass cannot persist a proper
handoff; it is not evidence of useful progress.

Treat a runtime-synthesized degraded checkpoint as a continuity aid that needs
fresh validation, not as proof that the prior session completed its intended
handoff. Never bypass skill authorization or protected schedule control merely
because the Objective policy requires this skill.

## Monitor Objective Health

Inspect desired outcome, success criteria, progress summary, current focus,
status, event log, and linked plans, tasks, schedules, and heartbeat items at
strategic checkpoints.

Update objective progress and status after health decisions. Map:

- healthy pursuit to `ACTIVE`
- a named external or internal prevention condition to `BLOCKED`
- deferment to `PAUSED`, with reason, owner, resume condition or review date in
  durable state and history
- evidenced completion to `SATISFIED`
- unattainable accepted conditions to `FAILED`
- sponsor withdrawal to `CANCELLED`
- authorized terminal discontinuation to `ABANDONED`
- an authenticated recoverable deletion in progress to `DELETING`, followed by
  the retained tombstone state `DELETED`

Never use `SATISFIED` for abandonment, deferment, partial work, or task-level
completion. Cascade lifecycle changes through objective-owned links and
reconcile in-flight work.

## Monitor Loops and Recover

Use status for liveness and pressure, task history for actual progress events,
and the execution digest for current goal distance. Never treat a fresh status
response as proof of progress.

Use runtime retry and delivery recovery before model-level repetition. Record a
recovery-aware plan action when leaving the happy path. Start isolated recovery
with a compact failure snapshot when context contamination or pressure makes
inline recovery unhealthy.

Do not forge manager-control messages, manipulate hidden identifiers, or use
shared persisted state as an inter-agent communication channel.

## Preserve Authorization

Treat conversational confirmation as agreement rather than authenticated
authority. Let the access service's decisions and mandatory local guards
control protected actions. Keep access, invocation, schedule, settings,
credentials, provisioning, and skill lifecycle authorities distinct.

Read the `reason` and `next_step` of an `access_denied` result first. If the
access check could not run, report the blocker and follow the returned operator
repair step; a new permission request cannot restore the service. Resume
dependent work only after the service is restored and access is checked again.
For a confirmed lack of permission, ask with `request_access` using the
`tool_id`, `operation`, and `level` the refusal names. Resume from the returned
decision without widening it.

When a worker asks with `request_access`, the runtime hands the access down at
once if TeamArchitect holds it and may hand it on without asking. Otherwise the
worker's task waits for a person in the Inbox and resumes with the decision.
Keep the parent waiting for its child result and record the access dependency;
do not restart the task as a new assignment.

An agent may recur in the task hierarchy: TeamArchitect can delegate a job whose
specialist needs a protected setup step from TeamArchitect. Keep that lineage
intact. TeamArchitect never approves access requests itself; a request its access
does not cover goes to a person in the Inbox. A missing requester route is a task
failure, not an access decision. Inspect the saved task before retrying; do not
ask for the same access again or copy a decision to another task merely because
delivery failed.

After an `access_denied` result and before calling `request_access`, write a
provisional Objective checkpoint, because the call may pause the source task at
once. Include the refused `tool_id`, operation, and level, the exact target and
observed state, dependent work, the resume condition, and a fresh resource
version or digest while checkpoint reserve remains; observe the target first if
you lack fresh state. Keep the source task non-terminal. Do not poll or retry
while waiting. A resumed call returns the saved decision without asking again.
Retry only when the result says `granted`. Re-observe the exact resource
identity, state, and digest first, because they may have changed during the
wait, and verify the resulting state after the operation. When the path closes,
record the access's level and lifetime from `list_my_access`. After a denial,
or a withdrawal because the task ended first, continue only with independent
work that neither performs nor approximates the denied effect.

## Respect Current Limits

Treat semantic objective-health review, procedure-fitness assessment, and
no-progress detection as manager behavior unless a runtime gate explicitly
enforces them. The Phase 1–2 work-session runtime enforces admission windows,
usage accounting, required-skill activation, and checkpoint persistence; it
does not infer semantic health, choose abandonment, or coordinate distributed
specialist budgets. Do not claim that a prompt, status signal, or skill
activation automatically enforces the complete SOP.

Transactional snapshot handoff and passing contention tests do not establish
production readiness for unrestricted parallel workers. The runtime still needs
single-writer manager commands, snapshot-writer incarnation fencing, atomic
Objective-to-Research admission, enforced workspace isolation, and long-term
storage policy. Keep concurrency within the operator-enabled, verified scope.

## Recurring specialist work

For an ordinary user-owned scheduled root task, select the named worker type and
configure its automatic worker policy with `configure_scheduled_worker`. Use
`create_scheduled_job` with `target_agent_type`, `worker_policy_json`, and
`requirements_json` when creating the job. Keep known-blocked jobs as inactive
drafts. Declare each requirement as a tool catalog id and one of its operations
(`find_tools` lists them); mark branch-dependent needs conditional and leave
`runtime_discovery` enabled for open-ended work. To change them, call
`configure_scheduled_worker` with the current revision and the complete new
`requirements_json`; it replaces the saved list whether automatic startup is on
or off. Confirm the result's `saved_requirements` and `summary` show the change.

Use `prepare_scheduled_job_access` to check requirements and
`authorize_scheduled_job_access(schedule_id, expected_revision)` to give the
worker type what TeamLead may hand on; the rest is listed for a person to give.
`prepare_scheduled_job_access` reports under `missing_access` the tools the worker
type or the schedule's owner does not hold yet. Recheck readiness before
activating the draft. Changes to schedules the runtime manages return
`approval_required` and are applied with `apply_change` after a person approves.
Use the returned policy revision for edits. Convert exact agent-ID targets only
with explicit `convert_exact_target=true`; let live claims finish under their
prior revision. Keep protected Objective and infrastructure schedules on their
existing purpose-specific workflows.

Inspect `inspect_scheduled_worker` after an unclaimed-occurrence review. Resolve
policy, type, readiness, or admission blockers before attempting another manual
start. Distinguish startup acknowledgement, transport readiness, durable admission,
and a terminal task result. A worker may retire between runs; retain the schedule
policy so the controller can cover the next occurrence. Do not publish a second
copy of a scheduled payload to NATS.

For a scheduled job's `access_denied` result, apply the checks in
**Preserve Authorization** first. If permission is missing, the worker calls
`request_access` with the `tool_id` and `level` it names. A person decides in
the Inbox while the run waits ("Keep" gives it to the job); give the job what
every run needs beforehand with `authorize_scheduled_job_access`. Ask with the default `lifetime="until_revoked"` for access
every run needs; `task` or `one_time` access ends with the run. For a tool the
catalog lacks or missing credentials, use `manager_escalation` with the schedule
and the tool ID. Wait through the existing task workflow and verify the actual
operation after repair. Never treat a review message as access.

Change shared rules through `agent.schedule_workers.defaults.<rule>` for the
team or `agent.schedule_worker_rules.<rule>` with agent-type scope. As TeamLead,
use `inspect_scheduled_worker` to check custom specialist eligibility, including
on unbound drafts. Check `eligibility.allowed_by_default_policy` before changing
eligibility: specialist types shipped with Universal Agents have local startup
permission by default. Preserve existing disables and operator denies. For a
team-written type that lacks permission, add the registered type through the
bounded `agent.schedule_workers.eligible_agent_types` setting, preserving existing
entries, then prepare access and configure the policy. Keep startup permission
separate from tool access. When a team-written definition changes, the schedule
pauses with `agent_definition_changed_review_required`; show the owner
`definition.changes` from the inspection and re-save with `suggested_refresh` after
the owner agrees. Code releases never pause a schedule.

Check `worker_configuration_supported` before changing a timer. Run new and
upgraded system memory-review timers through the local scheduler with MemReviewAgent;
do not send the scheduled payload over NATS. For old TeamArchitect-targeted memory
timers, direct the operator to the offline `scripts/upgrade_local_schedules.py`
procedure instead of creating a replacement timer. Preserve queued review jobs;
they alone do not block the upgrade. Use the preview's exact IDs to resolve claimed
jobs, including expired claims with uncertain outcomes, and saved unfinished worker
tasks. Require stopped team runtimes and completed old NATS deliveries before apply.
Do not delete records or mark reviews complete to clear an upgrade check. Keep
system-schedule edits on their staged approval path and verify actual review
jobs and results.
Check `list_my_access`, then ask for
missing access with `request_access` (`hand_on=true` for what workers will
use; a scheduled job's own access comes from `authorize_scheduled_job_access`);
respect denied requests. Read the scheduled-worker repair
reference in `runtime-operations-workflows` for tuning and completion checks.
Keep explicit operator denies, the kill switch, quotas, leases and timing
ceilings outside these edits.
Suspend automatic startup with the policy's `enabled=false`; use the separate
schedule or task controls when the intent is to pause work or cancel execution.

Use Settings → Tasks to inspect an owner's unfinished work grouped by agent,
or `/stop` for the TeamLead's task trees. When a queue is full, select the affected
agent. Distinguish **Purge this queue**, which preserves that agent's current
work, from `/stop all`, which also cancels current work. Remove only work the owner
has chosen to cancel. Preserve history and future schedules, verify freed capacity,
and resolve the schedule's existing authenticated review separately. Do not infer
invalid tasks from the count alone or delete runtime database rows.
Treat a control timeout as an unconfirmed outcome. Refresh Tasks or run `/stop`
before retrying removal; do not infer disconnection or repeat a purge automatically.

For a task queue safety notice, inspect the named task's recorded dependency.
The runtime removes invalid queue entries while preserving tasks and pending access requests,
and pauses a final review that has no recorded reason to wait. Resolve genuine
dependencies through their normal workflows. Do not resend the original request,
duplicate a scheduled occurrence, or delete database rows to bypass the wait.

For a stuck-task notice after host sleep, allow the runtime's one-minute
heartbeat refresh window (`event=liveness_monitor_paused`). Inspect task history
and current state before reporting progress: a cleared warning establishes only
that its reported condition ended. Distinguish automatic system maintenance,
which works for no person and tells administrators, from a person's request.
Do not resend work or start a replacement merely because of a historical notice.


### Correct review steps

Each workflow step names the kinds of change (`change_kinds`) and the tools with a
level (`tool_access`) it needs; requests made while it runs are shown on it. Correct
a step that names the wrong kind or tool with `revise_access_workflow_step` before
any request is linked to it, keeping the workflow and finished work. A request no
running step expects is still decided in the Inbox and listed as not on a step. For
an already-ended source task, follow the remaining-work recovery procedure rather
than impersonating that task.

Link the tool-returned workflow `review_url`. Never infer a published documentation
URL from a runtime skill name; use only pages confirmed by a documentation listing.

Recurring timer runs may share conversation history without being follow-up
requests. A successful no-change check may complete quietly; explicit follow-ups
and delegated subtasks must still return results. Diagnose suppression refusals
using the runtime's task, conversation, schedule and follow-up IDs.
Built-in procedural guidance is served at
`/docs/skills/runtime-operations-workflows?source=bundled`. Use the trusted internal
website base URL. A saved workflow's progress uses its returned `/workflows/<id>`
URL, never the documentation URL.

The Inbox lists access requests waiting for a person and notices that need no
decision. Do not ask again while a request waits; respect decided outcomes and
check `list_my_access` for current access. Scheduled and recovery requests may
have no chat conversation; they resume the waiting task when a person decides.


For abandoned expired review claims, preview the offline upgrade with
`--retire-expired-review-claims`. Apply only after stopping all team runtimes,
finishing old broker deliveries, and taking a full backup. The option preserves
content and marks the records inactive with an unknown outcome; it does not replay
or delete them. Keep live claims and saved unfinished or unsupported workers as
blockers. Let InternalImprovementAgent inspect cleanup metadata and archive exact
IDs in its maintenance runs; the cleanup tools are its fixed duties as a built-in
system agent, and those runs work for no person. If a cleanup call is still
refused (for example by an administrator's block), it reports the refusal to
TeamArchitect rather than asking again. Purge only archived content after
retention. Preserve recurring memory schedules.

### Inspect schedules and reviews without large inventories

- Use `get_schedule_telemetry()` for counts. Request `include_schedules=true`
  only when timing/claim metadata is needed; use `schedule_id` for one timer.
- Use `list_scheduled_jobs(limit=20, offset=0)` for summary pages and follow
  `next_offset`. Supply `schedule_id` to read one schedule's full details in
  bounded excerpts. Pass `detail.next_offset` as `details_offset` for the next
  excerpt, keeping `detail.sha256` unchanged; restart if it changes.
- Read supplied review IDs with `get_memory_review_job(review_job_id=...)`.
  Follow its `detail.next_offset` as `offset`, checking the same digest. Use
  `list_pending_memory_review_jobs` only for pending metadata for the current
  team, worker type and person (review tools show only jobs made for the
  person the task works for). Follow `next_offset`; never treat one page as
  all work.
- Restart pending-job pagination after job mutations. Do not create a Python
  environment or open raw database files to read ordinary inspection results.
  Treat reads as evidence only; preserve claim ownership and exact permission
  checks before processing work or changing schedules.

### Inspecting and managing the current user's queue

Use `list_task_queue` for your active execution roots, queue positions, blockers
and delegated children. Read task history before treating two roots as
duplicates. Use `control_task_queue` to pause runnable queued work, stop a
confirmed duplicate, or resume the retained task once its blockers are resolved.
Resume does not decide access requests, answer pending questions, or override
budget pauses. Report the blocker and exact task ID instead of creating another
copy. Self-status, own tool-result inspection and current-task history notes are
standard access and need no grant.
