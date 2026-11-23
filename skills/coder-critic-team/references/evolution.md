# Evolving and Fine-Tuning `coder-critic-team`

Load this reference when fine-tuning the skill, when Critic Observer reports
`fine_tune_due: true` (after every 10 completed runs without fine-tuning), or
before adding a durable rule to `SKILL.md`, `references/coder.md`,
`references/critic.md`, or `references/protocol.md`.

Never auto-edit skill files during a live implementation run. Live runs always
execute single-pass under the frozen skill. Fine-tuning is an **interactive**
offline step: the agent runs discovery and drafts gated proposals, and the user
must explicitly accept each change before it is applied.

## Rule-authoring hygiene (GUARD)

- **Scope specialized rules with `[iff <observable trigger>]`:** Attach every
  specialized rule to a concrete condition (a file type, git state, brief field,
  or tool action), such as `[iff brief.pull_request is set]` or
  `[iff the diff edits database migrations]`. Never add broad `[always]` rules
  that fire on already-solved tasks.
- **No action triggers in closing rules:** Closing and final-response sections
  may only interpret and report results; never add instructions there that
  trigger extra edits or writes.
- **Replace superseded rules completely:** When a rule changes, remove or
  replace the old wording rather than appending caveats.
- **Keep role files compact:** Target at most ~4,500 characters each for
  `references/coder.md` and `references/critic.md` so active prompt overhead
  stays bounded across revisions.

## Pinned invariants (do not weaken)

- The lead is the only `cct.py` writer and passes turn handoffs unchanged.
- The coder decides every critique except a blocking one the critic maintains,
  which the lead rules on.
- `ledger.jsonl` is append-only; corrections use `intervention` or `note`.
- Important discoveries and choices outside the authorized brief are raised with
  the user promptly, even when coder and critic agree.
- Layer-1 deterministic checks (`tests`, linters, `layer: "deterministic"`
  criteria) gate readiness; prose cannot override a failing deterministic check.

## Interactive 10-run fine-tuning protocol

When `critic-observer` reports `runs_since_tune >= 10` for `coder-critic-team`
(or the user asks to fine-tune):

1. **Propose the session:** At the end of the 10th run, tell the user the count
   (`10 / 10` runs since last fine-tune) and ask whether they want to run an
   interactive fine-tuning pass now or defer it. Wait for their go-ahead.
2. **Analyze (paired directional regret):** Inspect the last 10+ runs in Critic
   Observer (`/api/cct/runs` or MCP) and `stats.json` files in `cct-runs/`, plus
   the active **Rejection Ledger** (`list_skill_rejections("coder-critic-team")`,
   bounded to the latest 20 entries). Partition observed issues into:
   - **Regressed (fix first):** behaviors that previously worked and degraded
     after an earlier skill change (e.g., rising stalls, missed critiques that
     `project-review-process` had to catch, or increased `criteria_regressed`).
   - **Unsolved gaps:** recurring failure modes across runs.
   - **Mastered (pinned):** invariants performing cleanly that edits must not
     disturb.
   Never re-propose an entry verbatim from the Rejection Ledger.
3. **Assemble Fix + Guard slices:** Pick 3–5 recent runs illustrating the target
   failure mode (**fix slice**) and 5–10 stratified earlier successful runs
   (**guard slice** across repos and change types) so fixes do not cause
   forgetting on older workflows.
4. **Propose (`M = 2` parallel candidates + contrast):** Draft **two**
   independent candidate skill edits (prefer one with Claude Opus 5.5 and one
   with Gemini 4 Neon, both on `high`), evaluate both against the Fix + Guard
   slice, and contrast winner (`m+`) vs. loser (`m-`) to verify why the winner
   avoids over-triggering.
5. **Gate (Soft-HURT + `[iff]` repair):** Run the Soft-HURT gate
   (`critic-observer gate` or MCP `evaluate_soft_hurt_gate`):
   - Admit a candidate only when net gain strictly exceeds induced hurt
     (`gain > hurt`) with zero guard-slice regressions (`max_hurt_tasks = 0`, or
     at most `1` after repair).
   - If the winner fails only because of 1–3 isolated regressions, run at most
     one narrowing pass wrapping the new rule in a tighter `[iff <trigger>]`
     precondition and re-score.
6. **Interactive user approval (required):** Present the winning diff, the
   Fix/Guard evidence, the Soft-HURT gate output, and any `[iff]` narrowing to
   the user. Apply **only** the edits the user explicitly accepts.
7. **Record the outcome in Critic Observer:**
   - For accepted edits: apply the diff, run `quick_validate.py` and tests, and
     call `record_skill_tune(skill="coder-critic-team", ...)` (which resets the
     10-run counter).
   - For declined or gate-rejected proposals: call
     `record_skill_rejection(skill="coder-critic-team", ...)` so future sessions
     keep the lesson in the Rejection Ledger.
