---
name: build-project-room
description: Prepare a gated "project room" before drafting or synthesizing from messy source material. Use when an AI assistant or agent is asked to produce high-stakes or multi-source knowledge work, such as memos, reports, briefs, proposals, plans, board materials, research summaries, legal/business analysis, or multi-document writing where files may be stale, duplicated, contradictory, missing, or unevenly authoritative. The skill emphasizes bounded workspaces, source summaries, source inventory, conflict/missing-context review, duplicate handling, grounded drafting, refresh handling for newly added files, and explicit user verification gates before proceeding.
---

# Build Project Room

## Overview

Use this skill to turn a messy source set into a bounded, inspectable workspace before producing a final artifact. The operating rule is: do not draft until the sources, conflicts, gaps, and authority decisions are visible and verified.

For table formats, reusable artifact skeletons, and prompt patterns, read [artifact-templates.md](references/artifact-templates.md).

## Fit Check

Use the full gated workflow for substantial work where a bad synthesis would matter. Prefer a lighter approach when the user asks for a casual summary, a single-file rewrite, or a quick brainstorm.

Start by identifying:

- The final deliverable requested.
- The available source locations, connectors, URLs, or local folders.
- The likely risk of stale, missing, duplicated, or contradictory inputs.
- The user's expected verification style if they already specified one.

If the user has not named a workspace, create or propose a project-room folder near the relevant files. Preserve originals. Do not silently move, rewrite, deduplicate, or delete source files.

## Tool And Room Selection

Choose the smallest room that exposes the source set clearly:

- Use a local folder when sources include mixed file types, many files, code, exports, or anything that benefits from filesystem inspection.
- Use uploaded-document or project tools when the source set is small, already uploaded, and bounded by the tool.
- Use source-grounded notebook or research tools when the job is mostly source-bounded reading and citation.
- Use repo or code workspaces when source truth depends on folder trees, scripts, configuration, or generated artifacts.

Do not treat the tool as the room. The room is the bounded workspace plus the visible artifacts that show what the agent thinks is current, authoritative, duplicated, missing, or unsafe to use.

## Gate 0: Scope And Access

Before source inspection, confirm that the task has a bounded objective and that the required source locations are reachable.

Produce a short intake note with:

- Objective.
- Intended final artifact.
- Source locations to inspect.
- Explicit exclusions.
- Risks or unknowns that could affect reliability.

Stop and ask the user to verify Gate 0 when the source set, permissions, objective, or deliverable is ambiguous. Proceed without stopping only when the user already supplied all of those details clearly.

## Step 1: Build The Room

Create a bounded workspace for the job. The room can be a local folder, a repo subfolder, an uploaded-document project, or another tool-specific workspace, but it must expose the working artifacts plainly.

Recommended structure:

```text
project-room/
  originals/
  working/
  source-summaries.md
  inventory.md
  conflicts.md
  missing-context.md
  duplicates.md
  working-brief.md
  draft-grounding-audit.md
```

Keep originals immutable. Put copied or generated working files in `working/`. If a source cannot be copied because it lives in an external system, record its stable identifier, URL, export path, or retrieval notes in the inventory.

## Step 2: Source Summaries And Inventory

Inspect the source set before synthesizing. For every source, record path or identifier, type, date, apparent authority, current/superseded status, supported claims, limitations, and intended use.

Summarize each source before comparing across sources. The goal is to separate "what this source says" from "how this source fits the project." Use `source-summaries.md` for short per-source notes, then use `inventory.md` for authority, status, supported claims, limitations, and intended use.

Use `unknown` rather than guessing when metadata, authority, or recency is unclear.

## Gate 1: Inventory Review

Stop after the inventory is complete. Ask the user to verify:

- The important sources are included.
- No obvious source is missing.
- Current and authoritative sources are marked correctly.
- Superseded/background-only sources are not treated as primary.
- The intended use of each source is acceptable.

Do not produce the final deliverable until Gate 1 passes. If the user corrects the inventory, update it and repeat Gate 1.

## Step 3: Surface Problems

Create three review artifacts before drafting:

- `conflicts.md`: disagreements, mismatched names, inconsistent numbers, date/version conflicts, and recommended handling.
- `missing-context.md`: absent files, unsupported claims, unclear assumptions, missing decisions, and questions that affect the final work.
- `duplicates.md`: exact duplicates, likely duplicate exports, version families, and suspected older/newer copies.

Do not silently resolve conflicts or deduplicate files for the user. The agent finds and explains; the user decides.

## Gate 2: Problem Review

Stop after conflicts, missing context, and duplicate candidates are listed. Ask the user to verify:

- Which conflicts should be resolved, preserved, or flagged in the final artifact.
- Which missing items must be found before drafting.
- Which gaps can be handled by careful wording.
- Which duplicate/version family is authoritative.

If unresolved issues materially affect the requested deliverable, recommend pausing the draft until the user provides or approves the missing context. If the user accepts a risk, record that acceptance in `working-brief.md`.

## Step 4: Working Brief

Compile the verified decisions into `working-brief.md`. This is the contract for drafting.

Include:

- Final deliverable and audience.
- Authoritative sources by topic.
- Background-only sources.
- Resolved conflicts and rationale.
- Known gaps and wording constraints.
- Claims that require citations or source anchors.
- Any user-approved risks.

## Gate 3: Brief Approval

Stop before drafting. Ask the user to approve the working brief or correct it.

Proceed to drafting only after the user has approved the source authority decisions and known limitations. If the user wants no more stops, still keep the brief and audit artifacts updated.

## Step 5: Grounded Draft

Draft from the approved working brief, not directly from the raw source pile.

Use these drafting rules:

- Cite or anchor factual claims to the source inventory.
- Flag unsupported claims instead of smoothing over gaps.
- Prefer current authoritative sources for numbers and decisions.
- Use background sources only for context.
- Avoid blending versions unless the working brief explicitly allows it.
- Keep uncertain points visible.

The writing prompt should be short once the room is ready: name the approved room artifacts, state which sources are authoritative for which claims, and require unsupported claims to be flagged rather than smoothed over.

## Gate 4: Grounding Audit

Before calling the artifact finished, create `draft-grounding-audit.md` and verify:

- Each important factual claim maps to a source.
- Each cited source is marked current or otherwise approved for that use.
- Known conflicts were handled as approved.
- Missing context was not invented around.
- Duplicate/version risks did not leak into the draft.

Stop if the audit fails. Repair the room artifacts or the draft, then rerun Gate 4.

## Step 6: Refresh When Sources Change

When new files arrive after Gate 1, do not append them directly into drafting context. Refresh the room:

- Add or reference the new source without modifying originals.
- Summarize the new source.
- Update `inventory.md`, `conflicts.md`, `missing-context.md`, and `duplicates.md` if the new source changes authority, status, gaps, or version families.
- Update `working-brief.md` when drafting assumptions change.

Stop at the earliest affected gate. For example, a new background-only article may only need Gate 1 review, while a new operating plan that changes numbers may require Gates 1, 2, 3, and 4 again.

## Step 7: Delivery Receipt

When the user approves the final artifact, leave a concise receipt:

- Inputs inspected.
- Room artifacts produced or updated.
- Gates passed.
- Remaining risks.
- Final deliverable path or summary.

Do not include a full source transcript or large copyrighted source excerpts in the receipt. Summarize and cite source locations instead.
