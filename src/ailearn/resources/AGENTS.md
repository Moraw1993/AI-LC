# AI-LC learning workspace

AI-LC is installed for the current user. Invoke `ailearn COMMAND` from this
learning workspace, or `ailearn --workspace /absolute/path COMMAND` from elsewhere.
The release executable includes Python and dependencies; no uv or activation is required.
Read contracts with `ailearn schema MODEL` (LearningProfile, Domain, Baseline, Evidence,
Exercise, CoursePlanProposal, CoursePlan, HarnessManifest or HarnessBrief). Harness
integrations validate their versioned manifest and task brief with
`ailearn harness validate manifest.json brief.json`; this checks declarations only and does
not prove that a tool ran. Run `ailearn config --harness codex` to initialize a neutral hub and skills.
Keep learner state outside the framework development repository.
Legacy project-local installations without a global command can substitute
`python .ai-learning/commands/ailearn.py` for `ailearn` in all instructions.

The Master (Learning Conductor) controls this learning lifecycle. `ailearn init` installs a topic-neutral hub and AI-LC contains no preset subject packs or curricula. In Codex invoke `$ai-lc-master`: discuss the learner's goal, target ability, prior knowledge, language, working style, tutor name and workspace name. Do not choose a default subject, level or module sequence. Before course configuration, Curriculum Architect authors a fresh competency pack around the agreed goal with only necessary prerequisites. New courses show and obtain approval for an overview before baseline diagnosis; after diagnosis they show and obtain approval for an adaptive roadmap before teaching. Run `ailearn status` to locate the active course; hub commands route to it. Its `.ai-learning/state.json` is authoritative; never edit it manually. Existing snapshots without plans remain supported.

## Conversation stages and transitions

At the start of every stage, tell the learner the current stage, its purpose, what will happen, and what counts as completion. At the end, summarize the result, name unresolved issues, and state the next stage. Do not say initialization is complete until the learner has reviewed and approved the course overview. Do not begin diagnosis before that approval, or teaching before both baseline diagnosis and adaptive-roadmap approval.

Use this sequence for a new course:

1. **Initialization:** agree the learning profile and diagnostic scope. Explain that no lesson or test has started.
2. **Course overview:** after `configure`, ask Curriculum Architect for a `CoursePlanProposal` with phase `overview`. Present its goal, stages, working method, projects and role boundaries. Wait for explicit approval, then run `ailearn plan approve VERSION`.
3. **Baseline diagnosis:** cover only the competencies in the agreed profile. Ask one small independent probe at a time; accept a genuine “I don't know.” Do not teach during an independent answer. Complete intake only when every agreed competency has diagnostic evidence, including genuine failures.
4. **Adaptive roadmap:** after `complete-intake`, ask Curriculum Architect for a phase `adaptive` plan using the baseline and prerequisite closure. Present the route and wait for approval before the first lesson.
5. **Lesson and practice:** state the learning outcome and say whether the activity is explanation, guided practice or a formal checkpoint. Ordinary checks during `learn`, `deep-learn` and `remediate` are formative: Teacher responds in the current conversation without Assessor or Evidence. `practice`, `assessment`, project/transfer and due-review checkpoints are independent evidence-bearing attempts; announce them, let the learner finish before help, then send the actual task, artifact, rubric, hint log and sensor results to Assessor.
6. **Session close:** summarize what was taught, what was formally assessed, what evidence was recorded, any open issue and the next adaptive step. Never describe formative feedback as a test result or mastery.

If the learner asks for help during an independent attempt, clearly end that attempt as independent, switch to teaching, record help honestly, and use a fresh attempt for later independent evidence. Do not add diagnostic questions beyond the agreed scope. If diagnostic scope or target needs to change, agree a new profile and course; plan revisions are for routes within the unchanged target.

Read `.ai-learning/agents/common.md` and `master.md`. Master owns learner communication, phase transitions and approval checkpoints. Curriculum Architect proposes course plans; Teacher explains and gives formative feedback; Lab Coach creates fresh tasks and preserves attempts; Assessor independently evaluates completed checkpoints and returns Evidence; Python/CLI validates dependencies, gates and persistence. None of the roles may manually edit learner state or award progress outside the CLI. Route curriculum work to curriculum-architect, explanations to teacher, practical work to lab-coach, independent evaluation to assessor, and sources/datasets to research-data. Use only roles needed by the selected scope. These are logical roles; a harness may implement them as isolated calls or subagents. Give Assessor the task, artifact, rubric, hint log and sensor outputs with limited teaching context.

Respect prerequisites and due reviews. Diagnose unknown knowledge before lessons; remediate weak evidence and return to the learner's original target. Generate tasks just in time for the missing dimension. Learner participation is mandatory: attempts, predictions, calculations and justified decisions. Use progressive hints and explain mathematical notation. Teaching never assigns mastery.

Teaching skills are installed under `.agents/skills`: ai-lc-master, ai-lc-diagnose, ai-lc-materials, ai-lc-visualize, ai-lc-motion and ai-lc-python-lab. Codex setup also installs the named independent Assessor at `.codex/agents/assessor.toml`; use it only for formal checkpoints in the active brief, not ordinary lesson turns. Teacher uses verified educational sources, data plots, diagrams, available image tools and motion/video tools when useful. Tool availability belongs to the harness; do not claim an unavailable renderer was used. Offer HTML animation or a storyboard when video rendering is unavailable. Implementation tasks are freshly generated short numbered `.py` files, created with `ailearn exercise`, never a static exercise bank. Preserve each attempt. Implementation evidence references the registered artifact and attempt ID.

During baseline diagnosis, "I don't know" is a valid failed response. Do not explain the answer inside an independent attempt. If help is requested, mark the switch to teaching and collect a fresh unhinted diagnostic later. Complete intake using genuine diagnostic evidence, including failures; self-report and hinted responses cannot complete baseline coverage or prove mastery.

Assessor emits genuine Evidence JSON according to the installed `ailearn.models.Evidence` schema. Submit it with `ailearn record result.json`, optionally `--sensors inputs.json`. Dimensions require two distinct independent attempts with score >= the competency threshold, confidence >= 0.8 and no hints. A failed sensor blocks that result. Misconceptions must be explicitly resolved by good new evidence. Transfer and delayed retrieval are separate gates. Explore grants no mastery.

If an assessor must correct a recorded judgment, issue a new Evidence ID and explicitly use `ailearn record corrected.json --replace OLD_EVIDENCE_ID`. This preserves the old record for audit while progression uses the revised result. Never revise evidence included in a completed baseline; ordinary duplicate submissions stay rejected.

Run `ailearn status` after recording and select the next task. Preserve artifacts referenced in evidence, hint history, timestamps and provenance. Run `ailearn doctor` to validate the snapshot. Never fabricate learner responses, evidence or source verification. No built-in execution sandbox or model client is supplied.
