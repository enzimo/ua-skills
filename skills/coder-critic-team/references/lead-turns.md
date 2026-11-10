# Lead Turns

Record these with `cct.py post RUN_DIR --actor lead --file TURN.json`. Post a
worker's file with that worker as `--actor`; a worker's file can never carry a
lead turn. `cct.py` refuses a turn that is out of order or incomplete and says
why; nothing is recorded when it refuses.

These lead turns are accepted at any point: `intervention`, `note`, `limits`,
`acceptance`, `narrative`, `close`, a `review_result` with `"ran": false`, and,
once a review has findings, `finding_update`. A `review_result` from before
the run comes before the pull request turn; a review that ran on the pull
request and a `fix_request` come after it.

## Brief (`cct.py init RUN_DIR --brief BRIEF.json`)

```json
{
  "title": "Retry failed webhook deliveries with exponential backoff",
  "outcome": "Deliveries that fail transiently are retried with backoff and dead-lettered after the last attempt.",
  "features": ["Exponential backoff with full jitter", "Dead-letter store"],
  "acceptance_criteria": [
    "Retries 5xx and timeouts; never 4xx except 429",
    "No delivery is sent twice after a slow acknowledgement"
  ],
  "non_goals": ["No schema migrations", "No per-endpoint rate limiting"],
  "constraints": ["Python 3.11; no new runtime dependencies"],
  "context": {"objective": "Reliable outbound notifications", "plan_step": "3 of 5",
              "notes": "Step 4 adds per-endpoint limits."},
  "repo": {"name": "example-owner/relay", "path": "/work/relay", "base": "main",
           "branch": "feat/webhook-retry"},
  "pull_request": {"url": "https://github.com/example-owner/relay/pull/142", "number": 142},
  "workers": {
    "coder": {"runtime": "claude-code", "model": "claude-opus-5-5", "effort": "xhigh"},
    "critic": {"runtime": "claude-code", "model": "claude-opus-5-5", "effort": "xhigh"}
  },
  "extra_lenses": ["data_integrity"],
  "limits": {"max_checkpoints": 8, "stall_minutes": 45, "fix_rounds": 1},
  "follow_up_issues": "file"
}
```

- Write each acceptance criterion so a test or a reading of the code can
  decide it.
- Record the model and effort each worker actually runs with, not the
  requested ones. Leave out `effort` when the runtime does not apply one.
- `extra_lenses` may add `data_integrity`, `compatibility` and `operability`.
- `follow_up_issues` is `file` (the lead files non-blocking findings as
  issues) or `propose` (the report lists them as proposed issues).
- Give `pull_request` only when the work continues a pull request that already
  exists. The coder then pushes to it instead of opening one, and `cct.py`
  refuses a `pr` turn with another URL. Say in `constraints` what else to do
  with it, such as a new base or labels.
- The run folder must be new and outside the checkout.
- Create the work branch before `cct.py init`. It records the branch's head
  as the commit the run starts from, whatever `base` points to locally, and
  refuses an existing pull request's branch that is behind its upstream.

## Intervention

```json
{
  "type": "intervention",
  "reason": "blocker_dispute",
  "summary": "Reuse deliveries.attempt_token: it survives restarts and needs no migration.",
  "rulings": [{"item": "C17", "decision": "partial",
               "rationale": "Store the key in the existing attempt_token column."}],
  "actions": ["Told the coder to drop the in-memory cache."]
}
```

`reason` is one of `blocker_dispute`, `loop`, `stall`, `scope_drift`,
`tests_failing`, `worker_replaced`, `clarification`, `budget` or `other`.
The workers' next turn briefs show the `summary`, each ruling and each line of
`actions`, so write in `actions` what a worker must do or what you did.
`rulings` are optional, except that every critique waiting for a ruling needs
one before work continues. You can rule on a critique waiting for a ruling or
on a settled one; let a worker's pending turn on a critique finish first. A
ruling decides the critique for good: the critic cannot raise it again.

## Note

`{"type": "note", "text": "Coder restarted after its context filled up."}`
Notes are kept in the ledger but do not count toward any statistic.

## Limits

```json
{"type": "limits", "limits": {"fix_rounds": 2, "max_checkpoints": 12},
 "reason": "The person asked for one more fix round."}
```

Changes `max_checkpoints`, `stall_minutes` or `fix_rounds` from here on. The
brief keeps its original values.

## Review result

```json
{
  "type": "review_result",
  "verdict": "approve_with_changes",
  "guide": "pull-requests",
  "reviewers": ["General reviewer", "Evidence auditor", "Failure analyst"],
  "skipped": ["Cross-provider Failure analyst: Codex is not signed in"],
  "findings": [
    {"severity": "blocking", "confidence": "verified",
     "title": "A dead-letter write is lost while the database is briefly unavailable",
     "where": "src/relay/delivery/dead_letter.py:41",
     "scenario": "The final attempt fails during a 2-second database failover.",
     "direction": "Retry the write, then alert."},
    {"severity": "should_fix", "title": "One slow endpoint delays retries for every other endpoint",
     "matches_item": "C04"}
  ],
  "report_file": "review.md"
}
```

Record it once the pull request is open. Copy each finding's severity and
confidence from the review report.
`verdict` is `approve`, `approve_with_changes`, `needs_rework` or
`goal_unclear`. Set `matches_item` when the critic raised the same problem
during the build; the report counts these. When the review could not run,
record `{"type": "review_result", "ran": false, "reason": "..."}`.

### A review from before the run

When the run fixes the findings of a review that already ran, record that
review right after `cct.py init`, before the coder's plan:

```json
{
  "type": "review_result",
  "stage": "before_run",
  "verdict": "needs_rework",
  "reviewers": ["General reviewer", "Failure analyst", "Security reviewer"],
  "head_sha": "474defec",
  "source": "review run relay-142-a",
  "report_file": "review/report.md",
  "findings": [
    {"severity": "should_fix", "confidence": "verified", "ref": "GEN-1",
     "title": "One error in the watchdog's probe stops the whole scheduler pass",
     "where": "src/relay/watchdog.py:524", "scenario": "A reply fails verification mid-probe.",
     "direction": "Catch errors per target and keep the other answers."}
  ]
}
```

- `head_sha` is the commit the review read, `source` says where the review is
  recorded, and `ref` keeps the review's own label for a finding.
- `cct.py` numbers the findings `F1`, `F2` and so on. The plan brief lists
  them, each checkpoint names the ones it fixes in `addresses`, and the critic
  checks each fix against its finding.
- After the pull request turn, re-check every finding at the new head and
  record a `finding_update` for each. `cct.py state` lists the ones still to
  re-check.
- A second review of the fixed pull request is optional. Record it without
  `stage`; its findings continue the numbering.
- The report shows this review as "Earlier review", outside the timeline: it
  took none of the run's time.

## Fix request

`{"type": "fix_request", "findings": ["F1"], "note": "Fix only F1."}`
Send one or more open blocking findings once the pull request turn is recorded
and no coder-critic turn is pending.
`limits.fix_rounds` (default 1) caps the rounds; raise it with a `limits`
turn when the person asks for another. A finding still `open` after a round
can be sent again.

## Finding update

```json
{
  "type": "finding_update",
  "updates": [
    {"finding": "F1", "status": "fixed",
     "evidence": "test_dead_letter_survives_failover passes; the write is retried 3 times."},
    {"finding": "F2", "status": "issue_filed",
     "issue_url": "https://github.com/example-owner/relay/issues/143"},
    {"finding": "F3", "status": "proposed", "note": "Brief asks to propose, not file."}
  ]
}
```

`status` is `fixed` (needs `evidence`), `issue_filed` (needs `issue_url`), or
`open`, `proposed`, `accepted_risk` or `wont_fix` (each needs a `note`). For
`open`, the note says what is left and why it stays open; the report shows it,
and an open finding with a note is not counted as a gap. Each update replaces
the finding's earlier note and evidence. Update any finding at any time after
its review. After a fix round, give every finding the round addressed a
status, including `open` for one the fix did not resolve. Record
`accepted_risk` on a blocking finding only when the person accepts the risk.

Add `"matches_item": "C04"` to an update when a critique raised the same
problem as the finding. This is how a finding from an earlier review, recorded
before any critique existed, gets its link.

## Acceptance

```json
{"type": "acceptance", "criteria": [
  {"id": "A1", "status": "met", "evidence": "test_policy::test_retryable_statuses"},
  {"id": "A2", "status": "partial", "evidence": "Counts exported; delays only as a sum."}
]}
```

Give every criterion a status (`met`, `partial`, `unmet`, `unverified`) and
the evidence you checked: a test, a file and line, or a run.

## Narrative

```json
{"type": "narrative",
 "summary": "Three to five plain sentences: what was built, how the pair worked, what the review found and what is left.",
 "next_steps": ["Merge after a human review of C04 and C17"]}
```

Keep the summary under 130 words. Name the decisions a human should check.

## Close

`{"type": "close", "outcome": "ready_to_merge", "note": ""}`

`outcome` is `ready_to_merge`, `needs_attention`, `blocked` or `abandoned`.
Close at any point; the note says why when the run stops early.

- `abandoned` needs nothing else.
- `needs_attention` and `blocked` need a narrative.
- `ready_to_merge` also needs:
  - a pull request and a project review that ran, before the run or on the
    pull request;
  - every finding of a review from before the run re-checked after the pull
    request turn;
  - every critique settled;
  - every blocking finding fixed or an accepted risk;
  - no other finding left `open`: a fix, a follow-up, an accepted risk or
    `wont_fix` for each;
  - the acceptance checked, with no criterion unmet.
