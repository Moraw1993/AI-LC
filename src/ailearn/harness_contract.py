"""Provider-independent validation for harness manifests and AI-LC briefs."""

from ailearn.models import (
    HarnessBrief,
    HarnessCapability,
    HarnessCapabilityState,
    HarnessManifest,
    HarnessRole,
)


def required_capabilities(brief: HarnessBrief) -> set[HarnessCapability]:
    required = set(brief.required_capabilities)
    required.update({HarnessCapability.INSTRUCTION_ACCESS, HarnessCapability.LOCAL_CLI})
    if brief.assessment_checkpoint == "formal":
        if HarnessRole.ASSESSOR not in brief.roles:
            raise ValueError("formal assessment brief must route to the independent Assessor")
        required.add(HarnessCapability.FORMAL_ASSESSMENT)
    if brief.assessment_checkpoint == "formative" and HarnessRole.ASSESSOR in brief.roles:
        raise ValueError("formative brief must not route to the independent Assessor")
    if getattr(brief, "dimension", None) == "implementation":
        required.add(HarnessCapability.FILE_ARTIFACTS)
    return required


def validate_delivery(
    manifest_data: dict, brief_data: dict
) -> tuple[HarnessManifest, HarnessBrief]:
    """Validate one declared harness delivery without claiming tools were executed."""
    manifest = HarnessManifest.model_validate(manifest_data)
    brief = HarnessBrief.model_validate(brief_data)

    required = required_capabilities(brief)
    declared = manifest.capabilities.model_dump(mode="json")
    missing = sorted(
        capability.value
        for capability in required
        if declared[capability.value] != HarnessCapabilityState.AVAILABLE
    )
    if missing:
        raise ValueError(
            "harness does not declare required capabilities as available: " + ", ".join(missing)
        )
    return manifest, brief
