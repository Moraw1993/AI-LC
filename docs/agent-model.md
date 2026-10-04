# Agent model

| Role | Authority and boundary |
| --- | --- |
| Learning Conductor | Agree goal, ability, tutor/course identity and style; select phase and next role |
| Curriculum Architect | Competency DAG, outcomes, depth and recomposable roadmap |
| Teacher | Explanations, intuition, formalization and Socratic checks; no mastery decisions |
| Lab Coach | Active tasks, experiments, projects and progressive hints |
| Assessor | Independent dimension-level evidence from genuine learner artifacts |
| Research & Data | Source verification, dataset search and provenance |

The role files share `common.md`. Root workspace instructions explain loading and routing.
Agents are an external-harness integration, not Python objects pretending to reason.
`init` installs `$ai-lc-master` plus five teaching skills under `.agents/skills`, selecting
no subject or level. The Master-created LearningProfile stores the tutor's display name;
it is not a native Codex agent registration. Bootstrap has no learner evidence.
A harness may use separate model calls or isolated subagents. Logical isolation is required
for assessment: pass the learner response, task, rubric, hint log and sensor outputs, not
the Teacher's confidence that the learner understands.

Teacher progression: problem → motivation → intuition → tiny example → visualization →
notation with explained symbols → derivation/manual calculation → implementation →
interpretation. Lab Coach asks the learner to predict before execution when helpful and
tracks hint levels 0 through 5. Exceptions to attempt-first are allowed when direct
explanation has a clear pedagogical purpose; they remain exposure, not mastery.

Before curriculum design, Teacher uses `$ai-lc-diagnose` to gather relevant experience,
prerequisite knowledge and current topic ability. Assessor evaluates genuine unhinted
diagnostics, including "I don't know" failures. Explicit teaching switches require a new
independent probe afterwards. `complete-intake` requires coverage before planning.
Teaching tools are `$ai-lc-materials` (verified notes and sources), `$ai-lc-visualize`
(plots, diagrams, interactive visuals, available image tools), `$ai-lc-motion` (animation,
available motion/video renderers), and `$ai-lc-python-lab` (fresh short numbered .py files).
Availability is determined by the harness; use an honest fallback when rendering is absent.
Skills do not provide a provider client or learner-code execution sandbox.

The Assessor rubric: 0 no evidence, 1 major gaps, 2 partial reasoning, 3 correct independent
reasoning, 4 robust reasoning including limitations. Scores are not probabilities.
Confidence is separately reported. Output one Evidence object per attempt/dimension and
submit using the CLI. Mastery is computed by deterministic gates, never assigned by prose.

No provider is selected implicitly. Learner data, artifacts and external documents should
be treated as private or untrusted as appropriate. Sensors validate supplied inputs; a
provider cannot claim an execution was sandboxed by AI-LC.
