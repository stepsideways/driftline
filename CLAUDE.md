# driftline — Claude Code Context

## Token Economy
Defaults for spending tokens well. They are defaults, not limits: see the
last rule.

1. Gate: if a shell command or script can do it (search, rename, format,
   calculate), use that instead of model reasoning.
2. Route on an automatic gradient: without being asked, hand routine work
   that needs no advanced reasoning to a subagent on the lowest model
   tier that does it well. Smallest tier: lookups, searches, summaries,
   mechanical edits. Middle tier: routine coding and tests. Top tier:
   design, research, hard debugging. If a result falls short, step up
   one tier and retry rather than jumping to the top.
3. Scope: work from the goal, the exact files or lines, and what "done"
   looks like. If one of these is missing and cannot be inferred, ask once.
4. Isolate: one task per session. When the task changes, suggest a fresh
   session and offer a 5-line summary to carry over.
5. Delegate reading: run broad searches in a subagent and keep only the
   conclusion in the main context.
6. Cap output: give the diff or the answer, not a restatement of the work.
7. Keep this file short and stable so it stays cached.
8. Measure tokens per finished task, not per message.
9. Verify in the same turn: before starting, settle how the result will
   be checked (a test, an expected number, an example of good output),
   then run that check before reporting done. Rework costs double.
10. Trim tools: use only the tools the task needs. Do not load or call
    unrelated connectors unless the task asks for them. If many are
    attached, say so once so they can be disconnected.
11. Automate repeats: when the same ask comes up a third time, offer to
    write it once as a script (zero tokens afterwards) or a skill
    (loaded only when needed, unlike this file, which is always loaded).

Innovation comes first. These rules cut waste, not thinking. For design,
research, novel ideas, or hard debugging, spend whatever depth, model
tier, and exploration the problem needs, and say so in one line. Never
drop a promising idea, skip verification, or give a thinner answer to
save tokens.
