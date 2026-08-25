---
name: skill-creator
description: Guides creation and revision of agent skills that stabilize complex execution through scoped procedures, checkpoints, recovery paths, and behavioral verification. Applies when a reusable skill must be created, audited, or improved.
license: Complete terms in LICENSE.txt
---

# Skill creator

Create skills as procedural anchors for capable agents. Stabilize execution where long or noisy trajectories tend to drift. Do not use a skill as a general knowledge dump or a substitute for reasoning.

## Apply the operating principles

- Assume the agent already knows common facts, programming concepts, and ordinary tool usage.
- Include guidance only when it changes a decision, preserves a fragile order of operations, prevents a demonstrated failure, or defines observable completion.
- Preserve the user's intent, chosen tools, authorization boundaries, and task scope.
- Match specificity to risk. Fix the sequence only when deviation can cause a concrete failure. Otherwise state the outcome and decision criteria.
- Keep discovery cheap but effective. Give the skill a concise, discriminating name and description that identifies key capabilities instead of an exhaustive list.
- Keep the entrypoint short enough to remain usable during execution. Route conditional detail to references and load it only when needed.
- Prefer a narrow procedure that works reliably over a broad skill that attracts unrelated tasks.

## Follow the authoring workflow

### 1. Define the applicability boundary

Collect realistic requests that should activate the skill. Add near-miss requests that resemble the target but require a different skill or no skill.

Extract the following boundary:

- Name the task state or workflow that makes the skill useful.
- Name the evidence available when the skill should begin.
- Name confusable neighboring skills or ordinary tasks that should not activate it.
- Keep automatic discovery unless the user explicitly requires an explicit-only skill.

Ask only for missing information that would materially change this boundary. Infer routine details from the repository, current conversation, and available tools.

### 2. Gather execution evidence

Prefer real trajectories, test runs, incident notes, or user corrections over imagined best practices. Preserve success and failure labels when learning from traces. Do not blend failed branches into the successful procedure without marking the recovery lesson they provide.

For each useful trajectory:

1. Identify the first state that constrained the correct action.
2. Record decisions that changed the execution path.
3. Record ordering constraints that prevented breakage.
4. Record intermediate evidence that allowed safe continuation.
5. Record recognizable failure signals and the recovery that worked.
6. Record the final evidence that proved completion.

Remove incidental exploration, one-task residue, duplicated commands, and explanations that did not affect execution.

### 3. Extract the procedural anchor

Make the entrypoint answer these questions when they apply:

1. When does the procedure apply?
2. What must already be true?
3. What observable evidence proves completion?
4. Which decisions and actions must occur, and in what order?
5. Which checkpoints must pass before continuing?
6. Which failure signals require retry, adaptation, escalation, or stopping?
7. Which assumptions invalidate the procedure?

Do not force every skill into seven headings. Preserve the answers in the smallest structure that keeps the workflow stable.

### 4. Choose only useful resources

Add a resource only when it has a concrete execution role.

- Put repeated deterministic transformations or fragile tool operations in `scripts/`.
- Put decision-changing schemas, policies, mode-specific procedures, and maintained API details in `references/`.
- Put templates, images, fonts, boilerplate projects, and other output inputs in `assets/`.
- Keep simple skills self-contained. Do not create empty directories, sample files, duplicated quick references, or copied manuals.
- Link every reference from `SKILL.md` and state when to read it.
- Execute scripts without loading their full implementation when inspection is unnecessary. Test every new or changed script.

Keep facts in the entrypoint only when the agent must recall them throughout the procedure. Move conditional facts to a relevant reference.

### 5. Initialize a new skill

Run the initializer only for a skill that does not already exist:

```bash
python skills/skill-creator/scripts/init_skill.py <skill-name> --path <output-directory>
```

Request resource directories explicitly:

```bash
python skills/skill-creator/scripts/init_skill.py <skill-name> \
  --path <output-directory> \
  --resources scripts,references
```

Add `--examples` only when unfinished examples will help. Replace or remove every generated example before validation.

Use lowercase letters, digits, and single hyphens between words. Keep the name at 64 characters or fewer and match the directory name to the frontmatter name.

### 6. Write the entrypoint

Write all instructions in imperative or infinitive form. State the desired outcome, the reliable procedure, real constraints, recovery behavior, and verification evidence.

Write the frontmatter description in third person. Describe what the skill does and when it applies. Add a boundary when a nearby skill or ordinary workflow is likely to be confused with it. Avoid trigger-word catalogs and long lists of capabilities.

Keep permissions explicit. Do not treat skill activation as authorization for an external mutation, credential disclosure, retry loop, or expanded scope.

For credentialed workflows, check hydrated runtime authentication, environment variables, secret-file mounts, or credential stores before requesting new credentials. Never ask for secrets in chat. Direct users to the runtime credential collection form when new credentials are required.

For command-oriented Universal Agents skills, require `shell-execution-workflows` for shared process behavior. Keep domain skills limited to domain commands, flags, decision rules, and policy caveats. Do not duplicate the shared RTK, timeout, working-directory, result, broker, or loopback contract.

### 7. Test behavior

Validate observable behavior rather than the presence of preferred wording or headings.

For a substantial revision, compare these conditions when practical:

- Execute without a skill to establish the raw baseline.
- Execute with the current skill.
- Execute with the revised skill.
- Execute with the revised skill among similar distractors.
- Execute an out-of-scope near-miss request.

Measure task success, execution-layer failures, ignored or misapplied guidance, verification quality, inspected and activated skills, and context cost. Treat exact skill selection as a diagnostic signal. Do not reject a successful run merely because a related non-target skill contributed useful guidance.

Use an isolated temporary workspace for forward tests. Give an independent evaluator the realistic request, the skill, and only the raw artifacts needed to perform the task. Do not provide the intended answer or suspected defect. Skip independent delegation when the change is narrow, risk is low, or delegation is unavailable or unauthorized.

### 8. Validate and package

Run structural validation:

```bash
python skills/skill-creator/scripts/quick_validate.py skills/<skill-name>
```

Treat validation as a structural gate. Use it to check frontmatter, naming, directory identity, and unfinished generated content. Do not treat it as proof that the procedure improves decisions.

Package a completed skill when distribution is required:

```bash
python skills/skill-creator/scripts/package_skill.py skills/<skill-name> [output-directory]
```

Inspect the archive contents and test any packaged scripts before delivery.

### 9. Iterate from observed failures

Compare the revised result with its baseline. Trace each regression to a missing boundary, weak checkpoint, bad ordering constraint, misleading description, or unnecessary instruction.

Make the narrowest correction supported by evidence. Do not accumulate universal rules for every isolated failure. Split a skill when distinct procedures compete for attention. Merge skills only when they share the same applicability boundary and execution control.

Stop when the skill produces the required behavior, near-miss requests avoid misapplication, and further instructions add context without measurable benefit.
