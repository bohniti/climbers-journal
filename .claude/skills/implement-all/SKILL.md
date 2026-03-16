---
name: implement-all
description: Implement all remaining plan steps by looping /implement with /clear between each step.
---

# Implement All

## Role
You are an automation driver that repeatedly executes `/implement` until every step in the latest plan is complete.

## Before Starting
1. **Read `features/INDEX.md`** — count how many features are still `planned` or `in-progress`
2. **Read the latest plan in `plans/`** — count unchecked `[ ]` steps remaining

If there are zero unchecked steps, tell the user everything is already done and stop.

## Loop

Repeat the following cycle until the plan has no remaining unchecked `[ ]` steps:

1. **Run `/implement`** — this implements the next uncompleted step, reviews, ships, QAs, and retros
2. **Run `/clear`** — reset the context window so the next iteration starts fresh
3. **Re-read the latest plan** — check if any `[ ]` steps remain
4. If steps remain, go back to step 1
5. If all steps are `[x]`, exit the loop

## After All Steps Complete
1. Read `features/INDEX.md` one final time
2. Confirm to the user that all planned features are now implemented
3. List the features that were completed during this run
