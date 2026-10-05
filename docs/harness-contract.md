# Harness contract

AI-LC protocol version 1 defines a provider-independent envelope for capability
declarations and task briefs. Python validates the envelope and declared prerequisites;
the external harness still performs teaching, fresh task generation, tool use and semantic
assessment. This contract does not add another harness adapter or certify compatibility with
any harness beyond the existing Codex setup.

## Capability manifest

Create a JSON object matching `ailearn schema HarnessManifest`:

```json
{
  "schema_version": 1,
  "harness_id": "codex",
  "capabilities": {
    "instruction_access": "available",
    "local_cli": "available",
    "file_artifacts": "available",
    "formal_assessment": "available",
    "media_tools": "unknown",
    "sandbox_execution": "unknown"
  }
}
```

Every capability has one of three values:

| Value | Meaning | Satisfies a required capability? |
| --- | --- | --- |
| `available` | The harness declares that the capability is available for this task now. | Yes |
| `unavailable` | The harness declares that it cannot provide the capability. | No |
| `unknown` | Availability was not established. This is the default. | No |

The manifest is a harness declaration, not evidence that a tool ran or that an assessment
occurred. Set a capability to `available` only when the harness has actually exposed the
needed tool in the current context. `media_tools` is optional unless a brief explicitly
requires it. The AI-LC package supplies no execution sandbox and never runs learner code;
`sandbox_execution` describes an independently provided harness capability only.

## Task brief

Briefs emitted by onboarding, planning and session commands use a version-1 envelope with
`schema_version`, `phase`, `action`, a non-empty `roles` list and non-empty `instructions`. Even
wait-for-review briefs route to Master with an explicit instruction. Other AI-LC fields remain
available as protocol extensions and must be preserved by harness integrations. See
`ailearn schema HarnessBrief` for the full typed envelope. The six role identifiers are
`master`, `curriculum-architect`, `teacher`, `lab-coach`, `assessor` and `research-data`.

The contract validator requires instruction access and the local CLI for every brief. A
formal checkpoint must route to `assessor` and requires the declared
`formal_assessment` capability. An implementation-dimension task requires `file_artifacts`.
Briefs may list further requirements, such as `media_tools` or `sandbox_execution`. The
validator fails closed when a required capability is `unknown` or `unavailable`:

```sh
ailearn harness validate manifest.json brief.json
```

The command reads both files without opening or modifying learner state. It prints the
harness id, protocol version and required capabilities only after successful validation.
It does not invoke the harness, read learner artifacts, run code, or prove that a declared
tool completed the task. A harness must report unavailable tools honestly and must never
claim an assessment or sandbox execution based solely on a valid manifest.

## Compatibility fixture

`tests/fixtures/harness/codex-v1.json` exercises onboarding, plan review, formal diagnosis
and implementation brief shapes against the same protocol. The fixture marks media and
sandbox availability `unknown`; it is test data for the current Codex integration, not a
claim that every Codex environment exposes those tools. No second adapter is included in
this release.
