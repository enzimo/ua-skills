# Coder-Critic Protocol

This is the contract shared by the lead, the coder and the critic. Each worker
also has its own role file next to this one.

## Roles and authority

- **Lead.** Owns the brief: the outcome, acceptance criteria, non-goals and how
  the work fits the larger plan. Starts the workers, hands each turn to the
  right worker, records every turn in the ledger, and steps in when the pair is
  stuck. Rules on a blocking critique the critic maintains after the coder
  rejected it. Runs the project review and reports.
  Explains important discoveries and decisions to the user promptly, with
  evidence, impact and viable choices where applicable. Gets the user's
  decision before work depends on a choice outside the authorized brief;
  pair agreement does not replace that decision.
- **Coder.** Writes every line that goes into the pull request. Plans first,
  then builds in checkpoints. Has the final say on every critique except a
  maintained blocking one.
- **Critic.** Reads, never writes. Reviews the plan and each checkpoint
  through the lenses below and says what should change and why.

The lead is the only one who runs `cct.py`. It writes each worker's turn brief
to `turns/<role>-brief.md` in the run folder and hands the worker a short
message naming that file. A worker reads the brief, writes its turn as JSON to
`turns/<role>-next.json` and replies with the path and one line. A worker never
edits the ledger, another worker's files or the brief.

## The sequence

1. **Plan.** The coder explores the checkout and writes the plan. No code yet.
2. **Plan review.** The critic reviews the plan.
3. **Response.** The coder accepts, partly accepts or rejects each critique,
   with a rationale for anything not fully accepted. If everything is accepted,
   the coder starts building; the critic sees the decisions with its next turn.
4. **Last word.** If the coder rejected or partly accepted anything in the
   plan review, the critic gives one last word on each: withdraw, maintain or
   amend. The critic gets no further rebuttal.
5. **Final call.** The coder makes the final call on each maintained or amended
   critique and starts building. A **blocking** critique the critic maintains
   or amends goes to the lead instead, who rules on it against the brief.
6. **Checkpoints.** The coder builds to a natural stopping point, commits, runs
   the relevant tests and records a checkpoint. The critic reviews the commits
   since the last checkpoint. The coder answers each critique and carries on.
   At checkpoints the critic gets a last word only on a rejected or partly
   accepted blocking critique; everything else is the coder's call.
7. **Final review.** The coder marks the last checkpoint `"final": true`. The
   critic reviews the whole change as it will ship. If the coder changes code
   after the final review, it records another final checkpoint for the critic.
8. **Pull request.** The coder pushes and opens the pull request. When the
   brief names a pull request that already exists, the coder pushes to that
   one and opens no other. The pull request must be exactly the last reviewed
   checkpoint: `cct.py` refuses it while the branch has commits, changes or
   untracked files the critic has not seen.
9. **Project review and fix round.** The lead reviews the pull request. Blocking
   findings go back to the pair for one fix round: the coder fixes them in a
   checkpoint, the critic reviews it, the coder pushes, and the lead re-checks
   each one. Non-blocking findings become follow-up issues.

   A run can also start from a review that already ran. The lead records it
   before the plan, the briefs list its findings, each checkpoint names the
   findings it fixes, and after the pull request turn the lead re-checks every
   finding at the new head.
10. **Report.** The lead checks the acceptance criteria, writes the summary and
    publishes the report.

A checkpoint is a point where the critic's view can still change the next
step: after the tests for a unit, after a function or module, before a risky
refactor or an interface other code will depend on. Aim for a reviewable size
of roughly 50 to 250 changed lines. Write tests before or with the code they
cover.

## Lenses

The plan must say how it handles every core lens, or `n/a: <why>`. The critic
reviews through the same lenses. Use these identifiers:

| Lens | Asks |
| --- | --- |
| `intent` | Does this deliver the brief's outcome and criteria, and nothing the brief excludes? |
| `correctness` | Does it do the right thing for real inputs, edges and states? |
| `security` | Are trust boundaries, input handling, permissions and secrets safe? |
| `scalability` | Does it hold up as data, traffic and load grow? |
| `modularity` | Are responsibilities and interfaces in the right places? |
| `complexity` | Is anything more complicated than the problem needs? |
| `concurrency` | Is shared state safe under concurrent callers, workers or retries? |
| `failure_handling` | What happens on partial failure, timeouts, retries and restarts? |
| `testing` | Do the tests prove the behaviour and catch the likely regressions? |

The brief may add `data_integrity`, `compatibility` or `operability` when the
change touches persisted data, existing clients or deployment.

## Severity and confidence

Use the scale the project review uses, so critiques and review findings compare:

- `blocking`: shipping it would break the intent, correctness, security or data;
- `should_fix`: a real problem that is not a blocker;
- `consider`: an improvement worth weighing.

Confidence is `verified` (seen in code, tests or a run), `likely` or `possible`.

## Turn files

Write one JSON object, or a list of objects when one turn records two steps.
Plain strings everywhere; no Markdown tables. Item and finding IDs (`C01`,
`F1`) are assigned by `cct.py`; refer to them exactly.

### Coder: `plan`

```json
{
  "type": "plan",
  "summary": "One RetryPolicy and a scheduler hook; 6 units; 5 checkpoints.",
  "plan_file": "turns/plan.md",
  "units": [
    {"name": "RetryPolicy", "purpose": "Decides whether and when to retry a failed delivery."}
  ],
  "lenses": {
    "intent": "Covers A1-A5; per-endpoint limits stay out (non-goal 2).",
    "correctness": "Backoff computed from attempt number; property tests for bounds.",
    "security": "n/a: no new input surface or credentials.",
    "scalability": "...", "modularity": "...", "complexity": "...",
    "concurrency": "...", "failure_handling": "...", "testing": "..."
  },
  "checkpoints": ["Backoff schedule tests", "RetryPolicy and schedule_retry()"],
  "tests": ["Unit tests for the schedule bounds", "Worker integration test with a fake receiver"]
}
```

`plan_file` is optional: a longer plan written inside the run folder.

### Critic: `review`

```json
{
  "type": "review",
  "summary": "Sound plan; one blocker on duplicate delivery after a slow acknowledgement.",
  "items": [
    {
      "lens": "correctness",
      "severity": "blocking",
      "confidence": "likely",
      "title": "A slow acknowledgement can cause a second delivery",
      "where": "plan: schedule_retry()",
      "detail": "A receiver that processes the event but answers after the timeout is retried.",
      "suggestion": "Send an idempotency key and keep it across attempts."
    }
  ]
}
```

`items` may be empty. To raise again a critique the coder did not take in
full, add `"reraises": "C04"` and `"new_evidence"`. Without new evidence, do
not raise it again. An accepted critique or a lead ruling is final.

### Coder: `response` and `final_call`

```json
{
  "type": "response",
  "decisions": [
    {"item": "C01", "decision": "accept"},
    {"item": "C04", "decision": "reject",
     "rationale": "Out of scope (non-goal 2); max_in_flight=4 already bounds starvation."}
  ]
}
```

Answer exactly the critiques the turn brief lists. `decision` is `accept`,
`partial` or `reject`; a rationale is required for `partial` and `reject`.
`final_call` has the same shape and answers the maintained critiques.

### Critic: `rebuttal`

```json
{
  "type": "rebuttal",
  "positions": [
    {"item": "C04", "position": "maintain",
     "argument": "One endpoint with 4 slow in-flight requests still blocks the others' retries."}
  ]
}
```

`position` is `withdraw`, `maintain` or `amend` (add `amended_suggestion`).

### Coder: `checkpoint`

```json
{
  "type": "checkpoint",
  "title": "RetryPolicy and schedule_retry()",
  "notes": "Policy is a frozen dataclass; jitter injected for tests.",
  "tests": {"command": "pytest tests/retry -q", "passed": 21, "failed": 0},
  "deviations": ["Merged two planned units; the split added no clarity."],
  "addresses": ["F2", "F3"],
  "final": false
}
```

`addresses` is optional. Use it when the run fixes the findings of an earlier
review: list the findings this checkpoint fixes, by the IDs the turn brief
gives. The critic checks each fix against its finding.

Commit first, including new files: `cct.py` refuses a checkpoint while tracked
files have uncommitted changes or untracked files are neither committed nor
ignored. It records the commits since the last checkpoint and writes their
diff for the critic. Report the test counts from the actual run, or
`"tests": {"not_run": "<why>"}`.

### Coder: `pr`

```json
{"type": "pr", "url": "https://github.com/example-owner/relay/pull/142", "number": 142,
 "title": "Retry failed webhook deliveries with exponential backoff", "draft": true}
```

After the fix round, record `{"type": "pr", "url": "...", "update": true}` once
the fixes are pushed. When the brief names an existing pull request, record
that pull request's URL; `cct.py` refuses any other.

### A response and the next checkpoint in one turn

When the coder accepts every blocking critique, it may record its response and
keep working to the next checkpoint in the same turn. After the final review or
in the fix round, that next checkpoint holds the changes the response accepted:

```json
[
  {"type": "response", "decisions": [{"item": "C09", "decision": "accept"}]},
  {"type": "checkpoint", "title": "Worker integration", "tests": {"passed": 30, "failed": 0}}
]
```

`cct.py` checks the whole list first and records nothing if any part is out of
turn. A worker's file holds only that worker's turns.

### Lead turns

The lead records these with `cct.py post` as well: `intervention` (`reason`,
`summary`, optional `rulings` of `{item, decision, rationale}` and `actions`;
the next turn brief shows all of them), `note`,
`limits`, `review_result`, `fix_request`, `finding_update`, `acceptance`, `narrative`
and `close`. Their fields are in the skill's `references/lead-turns.md`.
