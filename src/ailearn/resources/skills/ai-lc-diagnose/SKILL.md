---
name: ai-lc-diagnose
description: Diagnose an AI-LC learner's prerequisite knowledge and current ability before planning lessons. Use for initial intake, uncertain foundations, or a learner who says they do not know.
---

# Diagnose before planning

Read `.ai-learning/agents/common.md`, `teacher.md`, and `assessor.md` in the active course.
Run `ailearn status` and `session` with its workspace path. Read the agreed intake profile,
diagnostic competencies and outcome/rubric definitions. Do not plan lessons before baseline.

Gather relevant experience, then ask one small fresh question at a time: explanation,
prediction or manual calculation, and a short implementation only when appropriate.
Use several representations when needed to distinguish recall from understanding.
Focus on prerequisites for starting the agreed topic and the learner's current ability
in it. Do not test the whole domain unnecessarily or confuse an unfamiliar term with
inability to reason. Tailor difficulty from genuine responses.

Keep diagnosis separate from teaching. If the learner says "I don't know", acknowledge
it as a legitimate answer. Assessor may record a failed diagnostic with score 0 and
high confidence in that observation; it never proves mastery. Do not explain the answer
and then mark the same attempt independent. If explanation is requested, clearly switch
to teaching, record hints/exposure, and later ask a fresh unhinted diagnostic.

Save actual answers in a course-relative artifact. Independent Assessor produces Evidence
JSON according to `ailearn.models.Evidence`, kind diagnostic, genuine independence and
hint count, and an honest confidence. Record using `ailearn record result.json`.
Python diagnostic tasks must use `$ai-lc-python-lab`; reference their registered path
and LNNN-TNNN-ANNN attempt ID for implementation evidence.

Once all agreed competencies have qualifying independent, unhinted diagnostic results
(including genuine failures), save a Baseline JSON with `summary` and `evidence_ids`.
Explain demonstrated strengths, gaps and uncertainty; never invent scores or answers.
Run `ailearn complete-intake baseline.json`. Only then ask Curriculum Architect to
recompose the plan. A baseline records a starting point; mastery still needs its usual gates.
