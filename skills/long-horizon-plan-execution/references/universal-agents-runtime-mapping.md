# Universal Agents Runtime Mapping

## Apply Runtime Primitives

Map the OODA operating model to Universal Agents without inventing identifiers,
side channels, or authority:

| OODA concept | Universal Agents mechanism |
| --- | --- |
| Team lead | `TeamArchitect` |
| Bounded execution | Structured `Task` |
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
| Durable wait | Schedules and heartbeat items |
| Lesson candidate | `AfterActionReport` |

Keep plan, objective, digest, and history state local to the manager or agent
that owns it. Send all inter-agent work through structured transport. Include
the required task-local context in every delegation.

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

- cadence and UTC schedule
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
material-work tool capacity, and the built-in operator envelope allows at most
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
only under `objective_execution_profiles/`; it does not activate the layer.
Tell the operator to append its workspace-relative path after the base layer in
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
authority. Let Cedar-compatible decisions and mandatory local guards control
protected actions. Keep attachment, invocation, schedule, settings,
credentials, provisioning, and skill lifecycle authorities distinct.

Request the exact missing authority only after the protected boundary exposes
it. Resume from the structured authenticated decision without expanding its
scope.

For a trusted operator-class denial, `request_access` may route an exact
profile-eligible TeamArchitect action to the durable **Settings → Inbox**.
This is a wait for an authenticated team administrator, not a role assignment
or conversational approval. Administrator elevation is limited to the exact
agent, team, acting user, task, action, resource, capability, target-profile
digest, expiry, and remaining uses. It cannot become persistent or delegate.
After receiving the denial and before calling `request_access`, write a
provisional Objective checkpoint because the call may suspend the source task
immediately. Include the receipt, exact target and observed state, dependent
work, resume condition, and a fresh resource version or digest while checkpoint
reserve remains; observe the target first if the denial does not contain that
fresh state. Keep the source task non-terminal. Rely on the gateway to present
an administrator queue only when the trusted interrupt confirms eligibility.
A deterministic-review result has no user prompt and must not be polled or
retried. Resume the same task only from the
structured decision. Re-observe the exact resource identity, state, and digest
before retry because they may have changed during the wait, verify the resulting
state after the operation, and record only the lease consumption, remaining-use,
expiry, or revocation state exposed by a trusted runtime or administrator view
when the path closes. After denial or timeout, continue only with independent
work that neither performs nor approximates the denied effect.

## Respect Current Limits

Treat semantic objective-health review, procedure-fitness assessment, and
no-progress detection as manager behavior unless a runtime gate explicitly
enforces them. The Phase 1–2 work-session runtime enforces admission windows,
usage accounting, required-skill activation, and checkpoint persistence; it
does not infer semantic health, choose abandonment, or coordinate distributed
specialist budgets. Do not claim that a prompt, status signal, or skill
activation automatically enforces the complete SOP.
