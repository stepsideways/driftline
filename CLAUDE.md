# driftline: Claude Code context

## Token Economy
Defaults, not limits. A stricter rule elsewhere in this file, or in the
platform canon (Intuitive-core `CLAUDE.md`), wins. The final paragraph
overrides the rules below.

1. Gate: use a shell command or script, not model reasoning, for search,
   rename, format and calculation.
2. Route: hand routine work to a subagent on the lowest model tier that
   does it well. Smallest: lookups, searches, summaries, mechanical
   edits. Middle: routine coding and tests. Top: design, research, hard
   debugging. Step up one tier on a weak result. Regulated or costly-to-
   get-wrong work (clinical logic, patent and IP language, risk and
   regulatory files) stays on the top tier; when unsure, treat it as
   regulated. Keep work that is only a few tool calls in the main
   session; a subagent costs more than it saves there.
3. Read narrowly: search, or read line ranges, before reading whole
   files. Send broad searches to a subagent and keep only its conclusion.
4. Scope: work from the goal, the exact files or lines, and the check
   that proves "done". If one is missing and cannot be inferred, ask once.
5. Verify: run that check before reporting done. Rework costs double.
6. Output: give the diff or the answer, not a restatement of the work.
7. Sessions: one task each. When the task changes, suggest a fresh
   session and offer a 5-line summary to carry over.
8. Tools: use only what the task needs. If unrelated connectors are
   attached, say so once so they can be disconnected.
9. Repeats: on the third identical ask, offer a script (zero tokens
   afterwards) or a skill (loaded only when needed).

Innovation comes first. These rules cut waste, not thinking. For design,
research, novel ideas or hard debugging, spend whatever depth, model
tier and exploration the problem needs, and say so in one line. Never
drop a promising idea, skip verification or give a thinner answer to
save tokens.

When editing this file, keep it short and stable: it is loaded in every
session.
