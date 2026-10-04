# AI-LC learning workspace

AI-LC is installed for the current user. Invoke `ailearn COMMAND` from this
learning workspace, or `ailearn --workspace /absolute/path COMMAND` from elsewhere.
The release executable includes Python and dependencies; no uv or activation is required.
Read contracts with `ailearn schema MODEL` (LearningProfile, Domain, Baseline, Evidence,
or Exercise). Run `ailearn config --harness codex` to initialize a neutral hub and skills.
Keep learner state outside the framework development repository.
Legacy project-local installations without a global command can substitute
`python .ai-learning/commands/ailearn.py` for `ailearn` in all instructions.

The Master (Learning Conductor) controls this learning lifecycle. `ailearn init` installs a topic-neutral hub. In Codex invoke `$ai-lc-master`: first discuss the learner's goal, target ability, prior knowledge, language, working style, tutor name and workspace name. Do not choose a default subject or level. Master configures a separate course and Teacher diagnoses relevant prerequisites and current ability before Curriculum Architect plans lessons. Run `ailearn status` to locate the active course; hub commands route to it. Its `.ai-learning/state.json` is authoritative; never edit derived knowledge manually. Existing v0.1 course snapshots remain supported without automatic conversion.

Read `.ai-learning/agents/common.md` and `master.md`. Route curriculum work to curriculum-architect, explanations to teacher, practical work to lab-coach, independent evaluation to assessor, and sources/datasets to research-data. Use only roles needed by the selected scope. These are logical roles; a harness may implement them as isolated calls or subagents. For ordinary lesson answers, Teacher responds formatively in the current conversation without invoking Assessor or recording Evidence. Use an independent Assessor only after a completed formal checkpoint named in the current brief. Give Assessor the task, artifact, rubric, hint log and sensor outputs with limited teaching context.

Respect prerequisites and due reviews. Diagnose unknown knowledge before lessons; remediate weak evidence and return to the learner's original target. Generate tasks just in time for the missing dimension. Learner participation is mandatory: attempts, predictions, calculations and justified decisions. Use progressive hints and explain mathematical notation. Teaching never assigns mastery.

Teaching skills are installed under `.agents/skills`: ai-lc-master, ai-lc-diagnose, ai-lc-materials, ai-lc-visualize, ai-lc-motion and ai-lc-python-lab. Codex setup also installs the named independent Assessor at `.codex/agents/assessor.toml`; use it only for formal checkpoints in the active brief, not ordinary lesson turns. Teacher uses verified educational sources, data plots, diagrams, available image tools and motion/video tools when useful. Tool availability belongs to the harness; do not claim an unavailable renderer was used. Offer HTML animation or a storyboard when video rendering is unavailable. Implementation tasks are freshly generated short numbered `.py` files, created with `ailearn exercise`, never a static exercise bank. Preserve each attempt. Implementation evidence references the registered artifact and attempt ID.

During baseline diagnosis, "I don't know" is a valid failed response. Do not explain the answer inside an independent attempt. If help is requested, mark the switch to teaching and collect a fresh unhinted diagnostic later. Complete intake using genuine diagnostic evidence, including failures; self-report and hinted responses cannot complete baseline coverage or prove mastery.

Assessor emits genuine Evidence JSON according to the installed `ailearn.models.Evidence` schema. Submit it with `ailearn record result.json`, optionally `--sensors inputs.json`. Dimensions require two distinct independent attempts with score >= the competency threshold, confidence >= 0.8 and no hints. A failed sensor blocks that result. Misconceptions must be explicitly resolved by good new evidence. Transfer and delayed retrieval are separate gates. Explore grants no mastery.

If an assessor must correct a recorded judgment, issue a new Evidence ID and explicitly use `ailearn record corrected.json --replace OLD_EVIDENCE_ID`. This preserves the old record for audit while progression uses the revised result. Never revise evidence included in a completed baseline; ordinary duplicate submissions stay rejected.

Run `ailearn status` after recording and select the next task. Preserve artifacts referenced in evidence, hint history, timestamps and provenance. Run `ailearn doctor` to validate the snapshot. Never fabricate learner responses, evidence or source verification. No built-in execution sandbox or model client is supplied.
