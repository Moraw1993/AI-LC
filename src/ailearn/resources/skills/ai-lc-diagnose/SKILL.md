---
name: ai-lc-diagnose
description: Diagnose an AI-LC learner's prerequisite knowledge and current ability before planning lessons. Use for initial intake, uncertain foundations, or a learner who says they do not know.
---

# Diagnose before planning

Read `.ai-learning/agents/common.md`, `teacher.md`, and `assessor.md` from the learning hub.
Run `ailearn status` and `session` from the hub. Read the agreed intake profile,
diagnostic competencies and outcome/rubric definitions. Do not begin diagnosis until the
overview plan is approved. Do not teach lessons before baseline completion and approval
of the adaptive plan.

Gather relevant experience, then ask one small fresh question at a time: explanation,
prediction or manual calculation, and a short implementation only when appropriate.
Use several representations when needed to distinguish recall from understanding.
Focus only on the agreed diagnostic competencies and prerequisites for starting the
agreed topic. Do not add questions outside that scope or test the whole domain
unnecessarily. Do not confuse unfamiliar vocabulary with inability to reason. Tailor
difficulty from genuine responses; ask follow-ups only when needed to clarify the current
competency's evidence.

Keep diagnosis separate from teaching. If the learner says "I don't know", acknowledge
it as a legitimate answer. Assessor may record a failed diagnostic with score 0 and
high confidence in that observation; it never proves mastery. Do not explain the answer
and then mark the same attempt independent. If explanation is requested, clearly switch
to teaching, record hints/exposure, and later ask a fresh unhinted diagnostic.

Save actual answers in a course-relative artifact. These are formal diagnostic checkpoints:
after a response is complete, independent Assessor produces Evidence JSON according to
`ailearn.models.Evidence`, kind diagnostic, genuine independence and hint count, and an
honest confidence. Ordinary lesson checks outside this diagnosis remain formative and do
not invoke Assessor or create Evidence. Record formal results using `ailearn record result.json`.
Python diagnostic tasks must use `$ai-lc-python-lab`; reference their registered path
and LNNN-TNNN-ANNN attempt ID for implementation evidence.

Once all agreed competencies have qualifying independent, unhinted diagnostic results
(including genuine failures), save a Baseline JSON with `summary` and `evidence_ids`.
Explain demonstrated strengths, gaps and uncertainty; never invent scores or answers.
Run `ailearn complete-intake baseline.json`. Then ask Curriculum Architect for an adaptive
`CoursePlanProposal`, present the route and wait for explicit learner approval before
starting lessons. A baseline records a starting point; mastery still needs its usual gates.
