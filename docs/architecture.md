# Architecture

`models.py` defines strict Pydantic contracts. `graph.py` loads packaged or additive YAML
packs, rejects duplicate IDs, dangling dependencies and cycles, and returns topological
prerequisite closures. The initialized snapshot embeds packs, ensuring future package
updates do not silently change an existing learner's curriculum.

`engine.py` is the deterministic Learning Conductor core. Initialization records learner
intent and target. Discovery selects an independent diagnostic of uncertain knowledge.
Curriculum design resolves target closure. Learning routes missing dimensions to practice
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
database or multi-file commit protocol to reconcile. `doctor` replays evidence and compares
derived knowledge. For backups, copy state.json while no writer is active; keep learner
artifacts alongside it.

`sensors.py` performs pure numerical, shape, finite-value, units, split, availability and
baseline checks. Semantic judgement stays in Assessor. No untrusted code is executed.
`data.py` defines metadata, requirements and provider protocols; provider registration and
discovery are explicit. Network access and model-provider concerns belong to the harness.
