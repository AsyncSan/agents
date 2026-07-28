"""Unit tests for the compliance-bundle orchestrator."""

import io
import json
import zipfile
from types import SimpleNamespace

from agentforge.compliance_bundle import (
    FRIA_TRIGGERING,
    REGULATION_REF,
    build_compliance_bundle,
)


def _agent(risk: str = "high") -> SimpleNamespace:
    return SimpleNamespace(
        id="credit-scorer-v1",
        name="Credit Scorer",
        description="Scores consumer credit applications",
        version=2,
        risk_class=risk,
        total_executions=100,
        success_count=90,
        trust_score=0.8,
        avg_duration_seconds=150.0,
        card={
            "capabilities": {
                "domain": "fintech",
                "description": "Scores consumer credit applications",
                "inputs": [{"name": "app", "type": "object", "required": True}],
                "outputs": [{"name": "score.json", "type": "json", "guaranteed": True}],
                "constraints": {},
                "tags": [],
            },
            "runtime": {"model": "anthropic/claude-sonnet-4-6", "tools": ["sql"]},
        },
    )


def _open(zip_bytes: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(zip_bytes))


class TestBundle:
    def test_credit_scoring_includes_fria(self):
        zip_bytes, manifest = build_compliance_bundle(_agent(), "credit_scoring")
        assert "fria" in manifest["included_artefacts"]
        assert manifest["use_case"]["triggers_fria"] is True

    def test_other_use_case_skips_fria(self):
        zip_bytes, manifest = build_compliance_bundle(_agent(), "other_high_risk")
        assert "fria" not in manifest["included_artefacts"]
        assert manifest["use_case"]["triggers_fria"] is False

    def test_all_pdfs_present_for_credit_scoring(self):
        zip_bytes, _ = build_compliance_bundle(_agent(), "credit_scoring")
        with _open(zip_bytes) as zf:
            names = set(zf.namelist())
        for required in [
            "manifest.json",
            "README.md",
            "payloads/annex-iv.json",
            "payloads/pmm-plan.json",
            "payloads/data-sheet.json",
            "payloads/eu-db.json",
        ]:
            assert required in names
        pdfs = [n for n in names if n.startswith("pdf/") and n.endswith(".pdf")]
        assert len(pdfs) == 5  # fria, annex iv, pmm, data sheet, eu db

    def test_zip_has_four_pdfs_when_fria_skipped(self):
        zip_bytes, _ = build_compliance_bundle(_agent(), "other_high_risk")
        with _open(zip_bytes) as zf:
            pdfs = [n for n in zf.namelist() if n.startswith("pdf/") and n.endswith(".pdf")]
        assert len(pdfs) == 4

    def test_manifest_regulation_ref(self):
        zip_bytes, manifest = build_compliance_bundle(_agent(), "credit_scoring")
        assert manifest["regulation"] == REGULATION_REF
        with _open(zip_bytes) as zf:
            stored_manifest = json.loads(zf.read("manifest.json"))
        assert stored_manifest["regulation"] == REGULATION_REF

    def test_all_pdfs_are_valid(self):
        zip_bytes, _ = build_compliance_bundle(_agent(), "credit_scoring")
        with _open(zip_bytes) as zf:
            for name in zf.namelist():
                if name.startswith("pdf/") and name.endswith(".pdf"):
                    content = zf.read(name)
                    assert content[:5] == b"%PDF-", f"{name} is not a valid PDF"

    def test_fria_triggering_set_complete(self):
        assert {"credit_scoring", "insurance_pricing", "public_service"} <= FRIA_TRIGGERING

    def test_provider_inputs_propagate_to_all_artefacts(self):
        zip_bytes, _ = build_compliance_bundle(
            _agent(),
            "credit_scoring",
            deployer_inputs={"deployer_organisation": "Acme Bank"},
            provider_inputs={
                "provider_name": "Acme Provider GmbH",
                "pmm_owner": "Head of AI",
            },
        )
        with _open(zip_bytes) as zf:
            annex = json.loads(zf.read("payloads/annex-iv.json"))
            pmm = json.loads(zf.read("payloads/pmm-plan.json"))
            fria = json.loads(zf.read("payloads/fria.json"))
        assert annex["section_1_general_description"]["provider_name"] == "Acme Provider GmbH"
        assert pmm["ownership"]["pmm_owner"] == "Head of AI"
        assert fria["deployer"]["organisation"] == "Acme Bank"

    def test_readme_lists_artefacts(self):
        zip_bytes, _ = build_compliance_bundle(_agent(), "credit_scoring")
        with _open(zip_bytes) as zf:
            readme = zf.read("README.md").decode()
        for needle in ["Annex IV", "Post-market monitoring", "Data governance", "EU database"]:
            assert needle in readme
