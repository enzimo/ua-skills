# Project Room Artifact Templates

Use these templates when the user has not supplied a preferred format. Keep them compact enough for a human to review at each gate.

## Intake Note

```markdown
# Intake

- Objective:
- Final artifact:
- Audience:
- Source locations:
- Explicit exclusions:
- Constraints:
- Known risks:
- Gate 0 status: pending | passed | blocked
```

## Source Inventory

```markdown
# Source Inventory

| ID | Source | Type | Date/version | Apparent authority | Status | Key claims or contents | Limitations | Intended use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | path-or-url | PDF/DOCX/CSV/transcript/etc. | known/unknown | primary/secondary/unclear | current/superseded/background/unknown | concise summary | caveats | authoritative/background/do-not-use |

## Inventory Questions

- Missing sources:
- Authority questions:
- Date/version questions:
- User corrections:
- Gate 1 status: pending | passed | blocked
```

## Source Summaries

```markdown
# Source Summaries

## S1: source title or path

- What it says:
- Important facts or decisions:
- Dates, versions, or metadata:
- What it does not establish:
- Summary confidence: high | medium | low
```

## Conflict Log

```markdown
# Conflict Log

| ID | Sources | Conflict | Why it matters | Recommended handling | User decision |
| --- | --- | --- | --- | --- | --- |
| C1 | S1 vs S3 | describe disagreement | impact on final work | use S1 / preserve ambiguity / ask user | pending |

## Gate 2 Conflict Decisions

- Resolved:
- Still open:
- Approved risks:
```

## Missing Context List

```markdown
# Missing Context

| ID | Gap | Evidence of gap | Impact | Recommended next step | User decision |
| --- | --- | --- | --- | --- | --- |
| M1 | missing file/decision/source | where gap appeared | high/medium/low | find source / phrase carefully / exclude claim | pending |
```

## Duplicate Report

```markdown
# Duplicate And Version Report

| ID | Sources | Similarity | Likely relationship | Risk | Recommended handling | User decision |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | S2, S5 | exact/near/version-family | newer/older/export/copy/unknown | overwrite/blending/overweighting | keep both, mark S5 authoritative | pending |
```

## Working Brief

```markdown
# Working Brief

## Deliverable

- Artifact:
- Audience:
- Purpose:
- Required format:

## Authority Decisions

- Authoritative for numbers:
- Authoritative for decisions:
- Authoritative for chronology:
- Background only:
- Do not use:

## Resolved Conflicts

- C1:

## Known Gaps And Constraints

- M1:

## Citation Or Grounding Requirements

- Claim types requiring source anchors:
- Required citation style:

## Gate 3 Approval

- Approved by:
- Date/time:
- Corrections:
```

## Grounding Audit

```markdown
# Draft Grounding Audit

| Draft section/claim | Source anchor | Source status | Pass/fail | Notes or repair |
| --- | --- | --- | --- | --- |
| claim summary | S1 | current/approved | pass/fail | notes |

## Gate 4 Result

- Unsupported claims found:
- Conflicts mishandled:
- Missing-context risks:
- Repairs made:
- Final status: pending | passed | blocked
```

## Delivery Receipt

```markdown
# Delivery Receipt

- Inputs inspected:
- Artifacts produced:
- Gates passed:
- Final deliverable:
- Remaining risks:
- Follow-up items:
```

## Prompt Patterns

Adapt these prompt patterns to the user's tool and source locations. Keep them as instructions to the agent, not as final deliverable text.

### 1. Room Builder For File-System Tools

```text
Build a project room for this job before drafting. Find the relevant materials in [folders/connectors/URLs]. Preserve originals. Create a bounded workspace with source summaries, a source inventory, a conflict log, a missing-context list, and a duplicate/version report. For each source, record path, type, date/version, apparent authority, current/superseded/background status, supported claims, limitations, and intended use. Do not write the final deliverable yet. Stop after the inventory and review artifacts are ready so I can verify them.
```

### 2. Inventory And Audit For Uploaded Docs

```text
Audit the uploaded documents before synthesizing. Summarize each document separately, then create a source inventory that identifies authoritative files, stale or background-only files, duplicates/version families, contradictions, and missing context. Do not draft the final artifact. Stop with the inventory, conflict log, missing-context list, and duplicate report for review.
```

### 3. Grounded Draft From An Approved Room

```text
Use the reviewed project room and working brief to draft [artifact]. Treat [source/source class] as authoritative for [claim type], [source/source class] as decision context, and [source/source class] as background only. Cite or anchor important claims to the source inventory. Flag unsupported claims instead of smoothing over gaps. Do not blend conflicting versions unless the working brief explicitly allows it.
```

### 4. Refresh Prompt For New Files

```text
Refresh the project room with these new files: [files]. Preserve originals. Summarize each new source, update the source inventory, and identify any new conflicts, missing context, duplicate/version issues, or changes to authority decisions. Tell me which gates need to be reviewed again before the current draft can be trusted.
```
