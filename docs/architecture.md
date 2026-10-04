# Architecture

`models.py` defines strict Pydantic contracts. `graph.py` loads packaged or additive YAML
packs, rejects duplicate IDs, dangling dependencies and cycles, and returns topological
prerequisite closures. The initialized snapshot embeds packs, ensuring future package
updates do not silently change an existing learner's curriculum.

`ailearn init` creates a neutral hub with bootstrap.json, logical role instructions and
native-discoverable `.agents/skills/*/SKILL.md` resources. It does not load a domain or
select a target. The external Master gathers explicit intent, target ability, previous
experience, language, style, tutor display name and course name. `configure` validates
a LearningProfile and packs, creates `workspaces/<name>`, and atomically publishes that
active course reference in the hub. Commands from the hub route to the active course;
commands from the course work directly. Reusing a name requires the same profile and packs.

Release distribution uses PyInstaller to bundle Python, dependencies and all ailearn
resources into one executable per OS/architecture. `scripts/build_native.py` verifies
the binary version and domain loading and writes SHA256 files. Tag builds validate the
package/tag version and publish binaries plus native shell/PowerShell installers.
Installers check checksums and executable versions before publishing immutable version
directories and selecting the user command. They never rewrite learner state.

`ailearn config --harness codex` installs a subject-neutral hub, six logical roles and
six native skills, plus `.codex/rules/ai-lc.rules` for deterministic read commands.
Existing Codex config.toml, sandbox settings and root AGENTS.md stay untouched.
Conflicting rules/resources fail; no provider settings or hooks are needed. Each file
publication is atomic, but hub bootstrap and rules are not a multi-file transaction.
A failed configuration can leave a valid hub; repeating the command safely completes it.

The legacy project-local installer remains compatible: `install.py` and `installer.py`
use temporary venv/pip to stage `.ai-lc/runtime`, with source/interpreter manifests.
Its `.ai-learning/commands/ailearn.py` launcher binds to its course/hub and discovers the
ancestor runtime. Legacy users substitute that command for `ailearn` when no global
command exists. Release usage requires no installed Python or uv; development uses uv.
`schema MODEL` exposes contracts without imports in an unknown interpreter.

`onboarding.py` gates modern course planning on a Baseline. Teacher gathers knowledge
and genuine responses; independent Assessor records diagnostic evidence. The agreed
diagnostic competencies must belong to the selected target's prerequisite closure.
Each needs independent, unhinted diagnostic coverage with confidence >= 0.8; an actual
failed answer qualifies as diagnosis, not mastery. Self-report, exposure and hints cannot
complete intake. `complete-intake` records a summary with validated evidence IDs.
The snapshot's optional intake preserves old v0.1 workspaces without invented baselines.
State loading checks profile/config agreement, diagnostic scope and baseline references.

`engine.py` is the deterministic Learning Conductor core. Before baseline completion,
session/plan briefs route to diagnosis regardless of requested learning scope. Curriculum
design then resolves target closure. Learning routes missing dimensions to practice
or remediation. Consolidation prioritizes delayed reviews and application selects unseen
transfer tasks. The external Master role invokes specialist instructions for each brief.
The session brief and its phase are persisted as an audit event.

Each competency has seven dimensions and a 0–4 threshold. Core dimensions depend on depth.
Two distinct qualifying attempts are necessary per dimension. Independent failure clears
previous success for that dimension, while hints do not establish mastery. Explanation and
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

`store.py` writes one authoritative snapshot by temporary-file replacement. State, evidence
and history commit together. An exclusive lock serializes CLI writers; a failed transaction
does not persist partial changes. Init stages the full directory and preserves existing
AGENTS.md. Exports are read views, not independently authoritative files. There is no
database or general multi-file commit protocol to reconcile. `doctor` replays evidence and compares
derived knowledge. For backups, copy state.json while no writer is active; keep learner
artifacts alongside it.

`exercises.py` creates <=80-line Python scaffolds with lesson/topic/attempt numbering,
validates AST syntax without execution, and registers metadata in the snapshot. Exclusive
creation preserves previous attempts. Publication failure rolls back the unchanged newly
created scaffold; a process crash may leave an unregistered file, which is never overwritten
automatically. Modern implementation evidence must match task path, ID, competency and kind.
CLI import and doctor check registered artifacts exist. All semantic grading and genuine
code execution remain external-harness responsibilities; no sandbox is supplied.

Teaching skills cover diagnosis, sourced materials, static/data/interactive visualizations,
image illustrations, motion/video explanations and Python labs. They are packaged workflows,
not installed media engines. The harness selects available tools and reports unavailable
rendering honestly. Master plus five specialist roles remain the reasoning boundary;
Python owns contracts, dependency graphs, gates, persistence and scheduling.

`sensors.py` performs pure numerical, shape, finite-value, units, split, availability and
baseline checks. Semantic judgement stays in Assessor. No untrusted code is executed.
`data.py` defines metadata, requirements and provider protocols; provider registration and
discovery are explicit. Network access and model-provider concerns belong to the harness.
