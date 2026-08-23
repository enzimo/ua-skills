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
does not time-box any Objective. Use the tools only after the user explicitly
accepts the time-boxed approach for that Objective. Treat a suggestion as inert.
Activate this skill through the normal protected `skills` tool during every new
session before material work.

At resume, load the canonical Objective, current Plan, latest checkpoint, and
recent evidence. Revalidate authority, procedures, stale evidence, and in-flight
effects before acting. Respect the runtime's safe boundary: stop starting new
subgoals and call `record_objective_work_checkpoint` while checkpoint reserve
remains. Record Observe, Orient, Decide, Act, Objective health, evidence delta,
completed and next subgoals, blockers, artifacts, and in-flight effects. Do not
turn activity counts into an invented completion percentage.

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

## Respect Current Limits

Treat semantic objective-health review, procedure-fitness assessment, and
no-progress detection as manager behavior unless a runtime gate explicitly
enforces them. The Phase 1–2 work-session runtime enforces admission windows,
usage accounting, required-skill activation, and checkpoint persistence; it
does not infer semantic health, choose abandonment, or coordinate distributed
specialist budgets. Do not claim that a prompt, status signal, or skill
activation automatically enforces the complete SOP.
