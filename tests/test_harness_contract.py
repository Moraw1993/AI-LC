import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ailearn.cli import main
from ailearn.harness_contract import validate_delivery
from ailearn.models import HarnessBrief, HarnessManifest

FIXTURE = Path(__file__).parent / "fixtures" / "harness" / "codex-v1.json"


def test_codex_fixture_obeys_versioned_harness_contract():
    fixture = json.loads(FIXTURE.read_text("utf-8"))
    manifest = HarnessManifest.model_validate(fixture["manifest"])
    assert manifest.schema_version == 1
    assert manifest.capabilities.media_tools == "unknown"
    assert manifest.capabilities.sandbox_execution == "unknown"

    for payload in fixture["briefs"]:
        checked_manifest, brief = validate_delivery(fixture["manifest"], payload)
        assert checked_manifest.harness_id == "codex"
        assert brief.schema_version == 1
        assert brief.model_dump(mode="json")["phase"] == payload["phase"]
    assert HarnessBrief.model_validate(fixture["briefs"][-1]).dimension == "implementation"


def test_cli_validates_manifest_and_brief_without_a_learning_workspace(tmp_path, capsys):
    fixture = json.loads(FIXTURE.read_text("utf-8"))
    manifest = tmp_path / "manifest.json"
    brief = tmp_path / "brief.json"
    manifest.write_text(json.dumps(fixture["manifest"]), "utf-8")
    brief.write_text(json.dumps(fixture["briefs"][2]), "utf-8")

    assert main(["harness", "validate", str(manifest), str(brief)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["declared_requirements_satisfied"] is True
    assert result["required_capabilities"] == [
        "formal_assessment",
        "instruction_access",
        "local_cli",
    ]

    fixture["manifest"]["capabilities"]["formal_assessment"] = "unknown"
    manifest.write_text(json.dumps(fixture["manifest"]), "utf-8")
    assert main(["harness", "validate", str(manifest), str(brief)]) == 2
    assert "formal_assessment" in capsys.readouterr().err


def test_unknown_capability_does_not_satisfy_a_brief_requirement():
    fixture = json.loads(FIXTURE.read_text("utf-8"))
    brief = {
        "schema_version": 1,
        "phase": "learning",
        "action": "render",
        "required_capabilities": ["media_tools"],
    }
    with pytest.raises(ValueError, match="media_tools"):
        validate_delivery(fixture["manifest"], brief)


def test_implementation_dimension_requires_file_artifacts():
    fixture = json.loads(FIXTURE.read_text("utf-8"))
    fixture["manifest"]["capabilities"]["file_artifacts"] = "unknown"
    brief = fixture["briefs"][-1]
    with pytest.raises(ValueError, match="file_artifacts"):
        validate_delivery(fixture["manifest"], brief)


def test_formal_assessment_requires_an_assessor_and_declared_capability():
    fixture = json.loads(FIXTURE.read_text("utf-8"))
    brief = {
        "schema_version": 1,
        "phase": "discovery",
        "action": "diagnostic",
        "roles": ["teacher"],
        "instructions": "Assess a completed response.",
        "assessment_checkpoint": "formal",
    }
    with pytest.raises(ValueError, match="independent Assessor"):
        validate_delivery(fixture["manifest"], brief)

    brief["roles"] = ["teacher", "assessor"]
    fixture["manifest"]["capabilities"]["formal_assessment"] = "unknown"
    with pytest.raises(ValueError, match="formal_assessment"):
        validate_delivery(fixture["manifest"], brief)


def test_manifest_rejects_unknown_capabilities():
    with pytest.raises(ValidationError, match="Extra inputs"):
        HarnessManifest.model_validate(
            {
                "schema_version": 1,
                "harness_id": "codex",
                "capabilities": {"executes_python": "available"},
            }
        )


def test_new_contract_schemas_are_public_without_workspace(tmp_path, capsys):
    for model in ["HarnessManifest", "HarnessBrief"]:
        assert main(["--workspace", str(tmp_path), "schema", model]) == 0
        assert json.loads(capsys.readouterr().out)["title"] == model
