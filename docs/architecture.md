# Architecture

`models.py` defines strict Pydantic contracts. `graph.py` loads course-authored YAML packs,
rejects duplicate IDs, dangling dependencies and cycles, and returns topological
prerequisite closures. The initialized snapshot embeds packs, ensuring future package
updates do not silently change an existing learner's curriculum.

`ailearn init` creates a neutral hub with bootstrap.json, logical role instructions and
native-discoverable `.agents/skills/*/SKILL.md` resources. It does not load a domain or
select a target. The external Master gathers explicit intent, target ability, previous
experience, language, style, tutor display name and course name. `configure` validates
a LearningProfile and course-authored packs, creates `workspaces/<name>`, enables versioned plan gates
for new courses, and atomically publishes that active course reference in the hub. New
learners approve an overview before diagnosis and an adaptive plan after baseline before
teaching. Commands run from the hub and route to the active course. A course stores its
state and learner artifacts; it does not receive duplicate hub roles, skills, or commands.
Course-specific instructions and agents can be added when needed. Reusing a name requires
the same profile and packs.

Release distribution uses PyInstaller to bundle Python, dependencies and all ailearn
resources into one executable per OS/architecture. `scripts/build_native.py` verifies
the binary version and public schema access and writes SHA256 files. The executable ships
no subject packs: agents create and validate course-specific packs after installation, and
each pack is embedded in that learner's snapshot. Tag builds validate the
package/tag version and publish binaries plus native shell/PowerShell installers.
Installers check checksums and executable versions before publishing immutable version
directories and selecting the user command. They never rewrite learner state.

`ailearn config --harness codex` installs a subject-neutral hub, six logical roles and
eight native skills, plus Teacher's two style guides under `agents/styles/` and
`.codex/rules/ai-lc.rules` for deterministic read commands.
Existing Codex config.toml, sandbox settings and root AGENTS.md stay untouched.
Conflicting rules/resources fail; no provider settings or hooks are needed. Each file
publication is atomic, but hub bootstrap and rules are not a multi-file transaction.
A failed configuration can leave a valid hub; repeating the command safely completes it.

The legacy project-local installer remains compatible: `install.py` and `installer.py`
use temporary venv/pip to stage `.ai-lc/runtime`, with source/interpreter manifests.
Standalone legacy workspaces retain their local `.ai-learning/commands/ailearn.py`
launcher, which discovers the ancestor runtime. Release usage requires no installed
Python or uv; development uses uv.
Legacy users substitute that command for `ailearn` when no global command exists.
`schema MODEL` exposes contracts without imports in an unknown interpreter. The
version-1 `HarnessManifest` and `HarnessBrief` contracts describe capability declarations
and a stable envelope shared by onboarding, planning and session briefs. `harness validate`
checks declared requirements without accessing learner state or running harness tools;
capability declarations are not proof that work was performed. Current compatibility
fixtures cover the existing Codex flow only; no second harness adapter is claimed.

`onboarding.py` gates new-course diagnosis on an approved overview and teaching on both
a Baseline and an approved adaptive plan. Course plans are typed, versioned proposals;
their stages cover every competency in the selected target's prerequisite closure exactly
once. Each proposal carries a versioned `LearningPathProfile` (`focused`, `balanced`, or
`project-led`); the learner approves it with the overview, and the adaptive plan must retain
that selection. The engine may reprioritize eligible project work by approved stage while
due reviews, remediation, prerequisites, evidence and mastery gates remain authoritative.
Snapshots predating the profile field read as `balanced`. Approval and revision decisions
are appended to history. Routine evidence-driven next-action changes need no approval.
Legacy snapshots default to no plan workflow and remain readable. Teacher gathers knowledge and genuine responses; independent Assessor
records diagnostic evidence. Diagnostic evidence stays within the agreed competency set.
Each needs independent, unhinted diagnostic coverage with confidence >= 0.8; an actual
failed answer qualifies as diagnosis, not mastery. Self-report, exposure and hints cannot
complete intake. `complete-intake` records a summary with validated evidence IDs.
The snapshot's optional intake preserves old v0.1 workspaces without invented baselines.
State loading checks profile/config agreement, diagnostic scope and baseline references.

`engine.py` is the deterministic Learning Conductor core. New-course session/plan briefs
route to overview proposal/approval, baseline diagnosis, then adaptive-plan
proposal/approval. Learning routes missing dimensions to practice or remediation only
after these gates. Consolidation prioritizes delayed reviews and application selects unseen
transfer tasks. The external Master role invokes specialist instructions for each brief.
Ordinary lesson checks are formative and stay with Teacher in the active conversation;
they do not create Evidence. Briefs mark whether a task is formative or a formal assessment
checkpoint, and only the latter route to an independent Assessor. Codex setup installs its
named Assessor profile for these checkpoints; other harnesses use their own isolated-call
mechanism. The session brief and its phase are persisted as an audit event.

Each competency has seven dimensions and a 0–4 threshold. Core dimensions depend on depth.
Two distinct qualifying attempts are necessary per dimension. Independent failure clears
previous success for that dimension, while hints do not establish mastery. Evidence IDs are
immutable; an explicit `record --replace OLD_ID` appends a correction linked by `supersedes_id`.
Only the active judgment contributes to gates while all revisions remain replayable audit data.
Completed baseline evidence cannot be revised. Explanation and
self-report evidence never passes. Active misconceptions block progression until a new
qualifying result explicitly resolves them. Transfer and retention gates lead to
TRANSFERABLE and RETAINED only after core evidence. Evidence carries assessor identity,
artifact reference, hint level, confidence, task kind, timestamp and structured sensors.

Review due dates start after core mastery. Successful delayed retrieval lengthens
intervals; failure resets to one day. The harness must change representations rather than
repeat the same prompt. Timestamps use aware UTC values; future or backdated submissions
are rejected. v0.1 scheduling is deliberately transparent, not statistically calibrated.
Failed delayed retrieval invalidates old passes across dimensions and requires renewed
core evidence. Transfer and retention cannot be submitted before core mastery. Pending
reviews of a regressed competency resume only after its core gate has been repaired.

`store.py` writes one authoritative snapshot by temporary-file replacement. State, course
plans, evidence and history commit together. An exclusive lock serializes CLI writers; a failed
transaction does not persist partial changes. Init stages the full directory and preserves
existing AGENTS.md. New audit events use a version-1 envelope with unique event IDs. They link
profile and plan versions, approval decisions, compact routing reasons and evidence IDs without
copying profile text or conversations. Loading validates versioned events while preserving
unversioned legacy entries unchanged; `history` and exports can read both. `doctor` validates
event envelopes and replays evidence to compare derived knowledge. Exports are read views, not
independently authoritative files. There is no database or general multi-file commit protocol
to reconcile. For backups, copy state.json while no writer is active; keep learner artifacts
alongside it.

`exercises.py` creates <=80-line Python scaffolds with lesson/topic/attempt numbering,
validates AST syntax without execution, and registers metadata in the snapshot. Exclusive
creation preserves previous attempts. Publication failure rolls back the unchanged newly
created scaffold; a process crash may leave an unregistered file, which is never overwritten
automatically. Modern implementation evidence must match task path, ID, competency and kind.
CLI import and doctor check registered artifacts exist. All semantic grading and genuine
code execution remain external-harness responsibilities; no sandbox is supplied.

Teaching skills cover diagnosis, lecture, laboratory, sourced materials,
static/data/interactive visualizations, image illustrations, motion/video explanations and
Python labs. Lecture and laboratory select teaching methods within the existing Teacher role;
the `lecturer` and `exercise_coach` style guides and shared mode policy are installed beside
the role instructions. They are packaged workflows, not installed media engines. The harness
selects available tools and reports unavailable rendering honestly. Master plus five specialist roles remain the reasoning boundary;
Python owns contracts, dependency graphs, gates, persistence and scheduling.

`sensors.py` performs pure numerical, shape, finite-value, units, split, availability and
baseline checks. Semantic judgement stays in Assessor. No untrusted code is executed.
`data.py` defines metadata, requirements and provider protocols; provider registration and
discovery are explicit. Network access and model-provider concerns belong to the harness.
