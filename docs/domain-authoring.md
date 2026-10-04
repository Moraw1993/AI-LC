# Domain authoring

Create one `.yml` file per pack. JSON is also valid YAML; built-ins use this representation
to keep escaping explicit. Copy a small built-in pack as a schema reference. Set:

- schema_version: 1, a unique domain ID, and a readable name;
- targets with nonempty beginner, mid and advanced competency lists;
- globally unique competency IDs such as `optimization.gradient_descent`;
- explicit prerequisites, including cross-domain IDs;
- outcomes for all seven dimensions, misconceptions and assessment strategies;
- a mastery threshold from 1 to 4 (default 3) and authoritative reference URLs.

Target levels select goal competencies; prerequisite closure defines required material.
All core outcomes through comprehensive depth must exist. Prerequisites may refer to
built-in packs or other custom packs loaded together. Duplicate packs or competencies
cannot override built-ins. Missing dependencies and cycles are errors.

```sh
# The project installer initializes a neutral hub.
# Master agrees an optimization profile after discussing the learner's goal.
python .ai-learning/commands/ailearn.py schema Domain
python .ai-learning/commands/ailearn.py configure profile.json --packs ./my-packs
```

The subject is not selected at init. Master and Curriculum Architect can author a pack
for any agreed topic; built-ins are starter examples. The profile supplies domain, explicit
target/depth and a small nonempty diagnostic competency subset from the target closure.
Map the learner's concrete desired ability to outcomes rather than imposing an arbitrary
target label. Competency modeling for diagnosis precedes lessons; curriculum design waits
for actual baseline evidence. No static exercise bank is permitted.

Packs are validated and embedded in the configured course snapshot. v0.1 has no in-place pack
migration; use a separate workspace when changing curriculum structure. Do not manually
rewrite snapshot packs in an active workspace.

Define outcomes and rubrics, not a pre-generated exercise bank. The harness uses the task
brief's missing dimension, difficulty, recent results and misconceptions to generate a new
exercise. Introduce specialized data providers by implementing `Provider.discover` and
registering it with `Registry`. Dataset metadata must identify provenance, definitions,
units, frequency, coverage and caveats. Requirements describe a search request; the
provider is responsible for checking observation count and characteristics before returning
candidate metadata. Synthetic results must be marked explicitly.
