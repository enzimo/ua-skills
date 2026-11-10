---
name: coder-critic-team
description: This skill should be used when a team lead hands a scoped code change to a supervised pair of agents, a coder that plans and writes all the code and a critic that reviews the plan and every checkpoint for intent, correctness, security, scalability, modularity, unnecessary complexity, concurrency, failure handling and testing. It covers the brief, the turn protocol and run ledger, stall detection and lead rulings, a new or existing pull request, a project-review-process review with one fix round or the fixing and re-checking of an earlier review's findings, a statistics report shown in T3 Code, as a hosted page in Universal Agents or as a standalone page, and the clean-up of a run after its pull request is merged. It should not be used for quick single-agent fixes, for reviewing an existing pull request, or for work that produces no code change.
---

# Coder-Critic Team

Run a code change with three agents. The **lead** owns the intent and
supervises. The **coder** writes every line, plan first, then in checkpoints.
The **critic** reviews the plan and each checkpoint while the work is still
cheap to change. The coder has the final say on each critique, except a
blocking critique the critic maintains after its last word; the lead rules
on that. When the pair finishes, the coder opens the pull request, or pushes
to the one the brief names. The lead then runs `project-review-process`, sends
any blocking findings back for one fix round, files the rest as follow-ups,
and reports with statistics. When a review already ran and the run is there to
fix its findings, the lead records that review first and re-checks each
finding at the end.

The lead stays out of the exchange. It hands each worker the turn brief
`cct.py` wrote, without changing it, watches for stalls, and steps in only
when the pair is stuck or drifting from the brief. Executing to intent outranks executing the
plan.

## Applicability

Use it for requests such as:

- "Have a coder and a critic implement retry with backoff for webhook deliveries."
- "Build this feature with a reviewer pair and report how it went."
- "Fix every finding of the review on pull request 101 and fit it onto the
  release branch."
- An Objective or plan step that needs a careful, reviewed implementation.

Do not use it for:

- A one-line fix or a change you can verify at a glance: make it directly.
- Reviewing an existing pull request or codebase: use `project-review-process`.
- A design or plan with no code yet: review it with `project-review-process`.
- A throwaway spike nobody will merge.

## Preconditions

- A git checkout of the repository with a known base branch. Either a way to
  push a branch and open a pull request, or the person's agreement to stop at
  a reviewed branch.
- A desired outcome that acceptance criteria can decide. Ask the person only
  the questions whose answers change the design.
- Python 3.9 or newer and `git` for the scripts.
- Worker models: Claude Opus 5.5 (`claude-opus-5-5`) at extra-high effort
  (`xhigh`) for both workers, unless the person chooses otherwise.

Run the scripts from this skill's `scripts/` folder: the folder the harness
loaded this skill from, or in Universal Agents the path
[references/runtimes.md](references/runtimes.md) gives. Below, `cct.py` and
`render_report.py` mean those scripts run with `python3`.

## Completion evidence

- The run's ledger is closed with an outcome.
- Every critique is settled: accepted, rejected with a rationale, withdrawn,
  or ruled on by the lead.
- A pull request holds the reviewed commits, or a note explains why none
  could be opened.
- The project review is recorded. Blocking findings are fixed and re-checked,
  or the run is closed as `needs_attention` or `blocked`. Non-blocking
  findings are filed or proposed as issues.
- Each acceptance criterion has a status and evidence.
- The report is where the person will see it: inline in T3 Code, a hosted
  page in Universal Agents, or a standalone file elsewhere.

## Procedure

1. **Write the brief.** Before you start, read
   [references/runtimes.md](references/runtimes.md) for your runtime and
   [references/lead-turns.md](references/lead-turns.md) for the brief's
   fields. The brief needs:
   - the outcome and features;
   - acceptance criteria a test or reading can decide;
   - non-goals and constraints;
   - how the change fits the larger Objective or plan;
   - the repository, base and work branch;
   - the pull request, when the work continues one that already exists;
   - the models and effort the workers will actually run with;
   - limits (checkpoints, stall minutes, fix rounds).

2. **Prepare the run.** Create the work branch and a worktree for the coder,
   and a new run folder outside the checkout. Then run
   `cct.py init RUN_DIR --brief brief.json`. This records the brief and copies
   `protocol.md`, `coder.md` and `critic.md` into `RUN_DIR/roles/`. It records
   the work branch's head as the commit the run starts from and prints it:
   checkpoint diffs and the report count only the commits after it. For an
   existing pull request, bring its branch up to date with the remote first;
   `init` refuses a branch that is behind.

   When a project review already ran and this run fixes its findings, record
   it now as a `review_result` with `"stage": "before_run"`. The workers'
   briefs then list the findings, and each checkpoint names the ones it fixes.

3. **Start the coder.** Run `cct.py turn RUN_DIR --for coder`. It writes the
   turn brief to `RUN_DIR/turns/coder-brief.md` and prints a short handoff
   that names the brief and, on a first turn, the role file and the protocol.
   Give the coder that handoff. Start the critic the same way when its first
   turn comes.

4. **Relay turns.** After each worker reply:
   1. Record its turn with
      `cct.py post RUN_DIR --actor <role> --file RUN_DIR/turns/<role>-next.json`.
      A worker's file can hold only that worker's turns. Write your own
      turns to `RUN_DIR/turns/lead-next.json` and post them with
      `--actor lead`. `cct.py post` deletes each `-next.json` file it records.
   2. Read the `Next:`, `Signal:` and `Handoff for the <role>:` lines.
      `cct.py post` has already written the next worker's brief.
   3. Pass the handoff to the named worker unchanged. Do not paste the brief,
      summarise it, add opinions or rank the critiques; that keeps you out of
      the exchange and keeps each relay to two lines.

   `cct.py turn RUN_DIR --for <role>` writes a brief again and prints its
   handoff. Add `--full` to print the whole brief for a worker that cannot
   read the run folder.

   The protocol settles the order:
   - plan, review, response, a last word on what was rejected, final call;
   - then checkpoints, each followed by a review and a response;
   - a final review, then the pull request.

   When the coder accepts every critique, the critic learns this from its
   next turn brief. No extra exchange is needed. When `cct.py post` refuses a
   turn, send its `Refused:` message back to the worker who wrote the turn.
   Do not fix the turn yourself.

5. **Watch and step in.** Run `cct.py state RUN_DIR` whenever you wake. Act on
   each signal, and record each intervention with its reason:

   | Signal or sight | Step in by |
   | --- | --- |
   | `blocker_dispute` | Read the critique, the coder's rationale and the critic's last word. Rule `accept`, `partial` or `reject` against the brief, with a rationale. |
   | `loop` (a critique raised again and again) | Rule on the root critique and say it is settled. |
   | `stall` | Check that the worker is alive. Start a fresh worker with its role file and turn brief if it died or lost its context (`worker_replaced`). |
   | `tests_failing` or `no_progress` | Ask the coder what blocks it. Unblock the environment, or rule on the design question behind it. |
   | `checkout_changed` (printed after a critic turn) | The tree was clean at the checkpoint, so the change is the critic's. Restore it and remind the critic that it reads only. |
   | `budget` | Raise the limit with a `limits` turn, narrow the scope within the brief, or stop and close as `needs_attention`. |
   | Plan or code drifting from the intent | Restate the brief and rule (`scope_drift`). |
   | A question the brief cannot answer and that changes the design | Ask the person, then record the answer (`clarification`). |

   Never write the code or the critique yourself. An intervention's summary
   and its `actions` both reach the workers in their next brief; put there
   what they must do.

6. **Take the pull request.** Check that the pull request exists and its
   checks run. `cct.py` refuses a `pr` turn until the branch is exactly the
   last checkpoint the critic reviewed. Changes after the final review need
   another final checkpoint first. When the brief names an existing pull
   request, the coder pushes to it and `cct.py` refuses any other URL.

7. **Run the project review.** Invoke `project-review-process` on the pull
   request, giving it the brief as the stated goal. Record a `review_result`
   with each finding's severity and confidence as the review reported them.
   Set `matches_item` where the critic raised the same problem.

   With a review from before the run on record, re-check each of its
   findings at the pull request's head instead: read the fix, or run the test
   or probe that reproduces the finding. Record `fixed` with evidence, or
   `open` with a note saying what is left. A new review of the pull request
   is then optional; record it as a second `review_result` when you run one.

8. **Fix blocking findings once.** For open blocking findings:
   1. Record a `fix_request`.
   2. The coder fixes them in a checkpoint, the critic reviews it, and the
      coder pushes and records a `pr` update.
   3. Re-check each finding against its scenario: read the fix, run the test
      that reproduces it, or re-run the reviewer view that found it.
   4. Record `fixed` with evidence, or `open` with a note saying what is left.

   The brief's `limits.fix_rounds` (default 1) caps the rounds. Instead of a
   fix round, a blocking finding can be recorded as `accepted_risk` when the
   person accepts the risk, or the run can be closed as `blocked`.

9. **File follow-ups.** For each non-blocking finding, check for an existing
   issue, then file one (`issue_filed`), or list it as `proposed` when the
   brief says `propose`.

10. **Close.**
    1. Record `acceptance` with evidence for every criterion.
    2. Record a `narrative`: three to five plain sentences, plus next steps.
       Name the critiques a human should check.
    3. Record `close`.
    4. Where the runtime allows, mark the draft pull request ready once no
       blocking finding is open.

11. **Report.** Run `cct.py stats RUN_DIR`. Universal Agents publishes the
    report from that `stats.json` as a hosted page. Elsewhere, render it:
    - `render_report.py RUN_DIR/stats.json --mode page --out RUN_DIR/report.html`;
    - in T3 Code, also `--mode t3 --out RUN_DIR/report-t3.html`. This is the
      compact view: every section and chart, with the long texts shortened.

    Deliver it as [references/runtimes.md](references/runtimes.md) describes:
    inline with `html_render` and the file's path in T3 Code, as a hosted page
    in Universal Agents (attached as a file when the team's Universal Agents
    cannot publish it), or as a file path elsewhere. Show the whole report;
    never split it or rebuild parts of it by hand. Give the person three to
    five lines: the outcome, the pull request link, what needs their
    decision, and where the report is.

12. **Clean up after the merge.** Leave the run as it is until its pull
    request is merged, often later, when the person says so. Leave an
    unmerged or abandoned run alone.
    1. Confirm the merge as [references/runtimes.md](references/runtimes.md)
       describes. `--merged` says you did; `cct.py` cannot check it.
    2. Run `cct.py tidy RUN_DIR --merged`. Add `--worktree` when the coder
       worked in a linked worktree made for the run, after `git fetch` in
       the main checkout so git sees the merge. `tidy` removes the
       run's working files, the ledger last, and keeps `stats.json` and the
       rendered reports. With `--worktree` it also removes that worktree,
       with its ignored files such as build output, and the local work
       branch, never the remote one.
    3. Read what it lists as left in place: those files are not the run's.
       Then remove what else your runtime lists.

    `tidy` refuses, and removes nothing, for a run that is not closed, was
    abandoned or has no pull request, without `--merged`, or when
    `stats.json` is missing or does not match the ledger. With `--worktree`
    it also refuses a main checkout, a locked or changed worktree, a head
    other than the last `pr` turn's, and a branch git would not delete
    without force. Its message says what to do.

## Failure recovery

| Failure | Response |
| --- | --- |
| `cct.py` prints `Refused:` | Nothing was recorded. Send the message to whoever wrote the turn. Never edit `ledger.jsonl`; it is append-only. Correct a recorded mistake with an `intervention` or `note`. |
| A worker crashed or ran out of context | Start a fresh one with its role file and `cct.py turn`. The ledger, the commits and the turn brief carry the state. |
| The critic changed the checkout | Restore the change, remind it, record a `note`. |
| No way to push or open a pull request | Stop before the pull request. Keep the reviewed branch and a `git format-patch` series in the run folder. Record `review_result` with `"ran": false`, a narrative, and `close` as `blocked`. Tell the person what is ready and what is missing. |
| `project-review-process` is unavailable | Record `review_result` with `"ran": false` and the reason. Do not substitute a different review without saying so. |
| A finding stays open on purpose | Record it `open` with a note. The report shows the note and does not count it as a gap. `ready_to_merge` still needs a follow-up, an accepted risk or a fix for it. |
| A blocking finding is still open after the fix round | Close as `needs_attention` or `blocked` and say what is left. Start another round only when the person asks; record a `limits` turn first. |
| The person changes the goal mid-run | Close the run as `abandoned` with a note. Start a new run with a new brief from the current branch. |
| `cct.py tidy` refuses or stops | A refusal removed nothing; a stopped tidy lists what it removed. Do what the message says and run it again. Do not work around a refusal by deleting the files yourself. |
| The run must stop early | Close at any point: `abandoned`, or `blocked` or `needs_attention` after a narrative. Then still render the report; it shows what was done and what is missing. |

## Resources

- [references/protocol.md](references/protocol.md): the sequence, lenses,
  severities and turn formats. Read it before the first turn; workers get a
  copy in the run folder.
- [references/coder.md](references/coder.md) and
  [references/critic.md](references/critic.md): the workers' role files,
  copied into the run folder by `cct.py init`.
- [references/lead-turns.md](references/lead-turns.md): the fields of the
  brief and the lead's turns. Read it when you record one.
- [references/runtimes.md](references/runtimes.md): starting workers, GitHub
  and report delivery in T3 Code, Claude Code, Codex and Universal Agents.
  Read your runtime's section before step 2.
- [references/report-design.md](references/report-design.md): the report's
  design. Read it only when changing the report.
- `scripts/cct.py`: the run ledger. Its commands are `init`, `post`, `state`,
  `turn`, `show`, `stats` and `tidy`.
- `scripts/render_report.py`: validates `stats.json` and renders it as
  script-free HTML, with `--mode page` or `--mode t3` and, when the default
  does not fit, `--detail full` or `--detail compact`.
- `assets/report.css`: the report's design tokens and styles.
