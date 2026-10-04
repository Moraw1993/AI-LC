# Domain authoring

AI-LC ships no subject packs, topic lists, sample curricula or prewritten exercises.
After the learner agrees on a concrete goal, Master asks Curriculum Architect to build a
course-specific YAML domain pack. JSON is also valid YAML. Before proposing topics, the
agent clarifies the target ability and uses the learner's experience and approved scope.

Each pack defines:

- schema_version: 1, a unique domain ID, and a readable name;
- one or more learner-goal target IDs mapped to the competencies needed for those goals;
- globally unique competency IDs such as `optimization.gradient_descent`;
- explicit prerequisite edges, including cross-domain IDs only when genuinely necessary;
- outcomes for all seven dimensions, relevant misconceptions and assessment strategies;
- mastery thresholds and authoritative references when applicable.

Prerequisite closure defines required material. Do not add familiar textbook topics merely
because they are usually taught in the subject. Keep the graph limited to the agreed goal;
explain why each prerequisite is needed and distinguish optional enrichment from required
competencies. Missing dependencies, duplicate IDs and cycles are errors.

```sh
# Initialize a neutral hub; no topic is selected.
ailearn config --harness codex
ailearn schema Domain
# Curriculum Architect writes a fresh pack under ./packs after agreeing the goal.
ailearn configure profile.json --packs ./packs
```

The profile names the agreed domain and target ID, target ability, depth and a small
nonempty diagnostic subset from that target's graph. Master presents the overview for
approval before diagnosis. After the baseline, Curriculum Architect designs the personalized
roadmap using the genuine diagnostic evidence; Master obtains approval before teaching.

Packs are validated and embedded in the configured course snapshot. v0.1 has no in-place
pack migration; use a separate workspace when changing curriculum structure. Do not
manually rewrite snapshot packs in an active workspace.

Define outcomes and rubrics, not a pre-generated exercise bank. The harness uses the task
brief's missing dimension, recent results and misconceptions to generate a new exercise.
Introduce specialized data providers by implementing `Provider.discover` and registering
it with `Registry`. Dataset metadata must identify provenance, definitions, units, frequency,
coverage and caveats. Requirements describe a search request; the provider checks observation
count and characteristics before returning candidate metadata. Synthetic results must be
marked explicitly.
