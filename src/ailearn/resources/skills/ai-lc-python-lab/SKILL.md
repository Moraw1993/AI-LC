---
name: ai-lc-python-lab
description: Create short, numbered Python exercises for AI-LC lessons, topics and attempts. Use for diagnostic implementation tasks, coding practice, retries and independent programming assessments.
---

# Short Python tasks

Read shared policy and Lab Coach instructions; use the active course's profile and brief.
Before baseline completion create diagnostic tasks only. Generate a fresh task for the
needed outcome and difficulty; never choose from a static exercise bank.

Read `ailearn schema Exercise`. Write a specification JSON with
lesson, topic, attempt (1..999), competency, kind (diagnostic/practice/assessment),
instructions and source. Each file addresses one focused problem. Include small inputs,
the expected interface and TODOs/pass for learner work, not the completed solution.
Include a manual check or expected properties without leaking an assessment answer.
Keep the entire generated file including comments at most 80 lines.

Run `ailearn exercise spec.json` with the active workspace or from its hub. The CLI
validates syntax without executing code and registers a file such as
`lessons/lesson_001_topic_002_attempt_003_statistics_mean.py` with ID `L001-T002-A003`.
Use returned metadata exactly. Reuse the lesson/topic for retries with increasing
attempt numbers; a lesson/topic stays tied to one competency. Never overwrite a previous
attempt or the learner's edits. Use a new lesson/topic when changing competency.

Ask for a prediction and learner implementation. Provide progressive hints only when
needed and log their actual level. Explain solutions only after the learner's attempt
or an explicit teaching switch. For implementation Evidence, reference the registered
relative file path, returned attempt ID, competency and matching task kind. Assessor
must inspect the genuine learner artifact separately from coaching context.

AI-LC supplies no execution sandbox. Do not run learner code without a real external
sandbox selected by the harness; AST syntax checks are not sandboxed execution.
If unavailable, report code inspection only and do not fabricate runtime sensor results.
