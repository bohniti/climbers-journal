---
name: implement
description: Implement the next step from the latest plan, then update project docs.
---

# Implementer

## Role
You are an engineer implementing the next uncompleted step from the latest plan.

## Before Starting
1. **Read CLAUDE.md** — understand tech stack, conventions, project structure
2. **Read `features/INDEX.md`** — know what exists
3. **Read all plans in `plans/`** — find the latest plan
4. **Identify the next uncompleted step** — look for the first step with unchecked `[ ]` items

## Implementation
1. Implement all tasks in the identified step
2. Verify the code works (run linters, start servers, etc.)

## After Implementation
1. **Update the plan** — mark completed items with `[x]`
2. **Update `CLAUDE.md`** — if tech stack, structure, or commands changed
3. **Update `features/INDEX.md`** — if feature status changed
4. **Update `docs/PRD.md`** — if scope changed
5. **REVIEW** Before you commit use the /review 
6. **Commit** — using the commit message specified in the plan step
