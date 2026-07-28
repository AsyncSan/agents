"""Unit tests for the AI Literacy training module and certificate generator."""

from datetime import datetime, timezone

import pytest

from agentforge.literacy import (
    CERTIFICATE_SCHEMA_VERSION,
    MODULES,
    PASS_THRESHOLD_PCT,
    REGULATION_REF,
    build_certificate,
    certificate_to_markdown,
    get_module,
    list_modules,
    score_answers,
)


class TestModuleCatalogue:
    def test_lists_all_modules(self):
        listing = list_modules()
        assert len(listing) == len(MODULES)
        for entry in listing:
            assert "id" in entry
            assert "title" in entry
            assert "slide_count" in entry
            assert "question_count" in entry

    def test_get_module_hides_correct_answers(self):
        module = get_module(MODULES[0]["id"])
        assert module is not None
        for q in module["questions"]:
            assert "correct" not in q
            assert "prompt" in q
            assert "options" in q

    def test_get_unknown_module_returns_none(self):
        assert get_module("does-not-exist") is None


class TestScoring:
    def test_all_correct_passes(self):
        module = MODULES[0]
        answers = {q["id"]: q["correct"] for q in module["questions"]}
        result = score_answers(module["id"], answers)
        assert result["score_pct"] == 100
        assert result["passed"] is True

    def test_zero_correct_fails(self):
        module = MODULES[0]
        answers = {q["id"]: (q["correct"] + 1) % len(q["options"]) for q in module["questions"]}
        result = score_answers(module["id"], answers)
        assert result["correct_count"] == 0
        assert result["passed"] is False

    def test_missing_answer_counts_as_wrong(self):
        module = MODULES[0]
        result = score_answers(module["id"], {})
        assert result["correct_count"] == 0

    def test_threshold_behaviour(self):
        module = MODULES[1]  # 4 questions
        correct = [q["correct"] for q in module["questions"]]
        answers = {
            module["questions"][0]["id"]: correct[0],
            module["questions"][1]["id"]: correct[1],
            module["questions"][2]["id"]: correct[2],
            module["questions"][3]["id"]: (correct[3] + 1) % 4,
        }
        result = score_answers(module["id"], answers)
        assert result["score_pct"] == 75
        assert result["passed"] is (75 >= PASS_THRESHOLD_PCT)

    def test_unknown_module_raises(self):
        with pytest.raises(ValueError):
            score_answers("does-not-exist", {})

    def test_breakdown_matches_submissions(self):
        module = MODULES[0]
        answers = {module["questions"][0]["id"]: module["questions"][0]["correct"]}
        result = score_answers(module["id"], answers)
        first = next(b for b in result["breakdown"] if b["id"] == module["questions"][0]["id"])
        assert first["is_correct"] is True


class TestCertificate:
    def _full_score(self):
        module = MODULES[0]
        answers = {q["id"]: q["correct"] for q in module["questions"]}
        return module["id"], score_answers(module["id"], answers)

    def test_certificate_contains_regulation_ref(self):
        module_id, score = self._full_score()
        cert = build_certificate("Alice", "Acme GmbH", module_id, score)
        assert cert["regulation"] == REGULATION_REF
        assert cert["schema_version"] == CERTIFICATE_SCHEMA_VERSION

    def test_learner_and_module_fields(self):
        module_id, score = self._full_score()
        cert = build_certificate("Alice Example", "Acme GmbH", module_id, score)
        assert cert["learner"]["name"] == "Alice Example"
        assert cert["learner"]["organisation"] == "Acme GmbH"
        assert cert["module"]["id"] == module_id

    def test_certificate_id_is_deterministic(self):
        module_id, score = self._full_score()
        completed = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        cert_a = build_certificate("Bob", "Acme", module_id, score, completed)
        cert_b = build_certificate("Bob", "Acme", module_id, score, completed)
        assert cert_a["certificate_id"] == cert_b["certificate_id"]

    def test_certificate_id_differs_across_learners(self):
        module_id, score = self._full_score()
        completed = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        cert_alice = build_certificate("Alice", "Acme", module_id, score, completed)
        cert_bob = build_certificate("Bob", "Acme", module_id, score, completed)
        assert cert_alice["certificate_id"] != cert_bob["certificate_id"]

    def test_markdown_renders_key_fields(self):
        module_id, score = self._full_score()
        cert = build_certificate("Alice", "Acme GmbH", module_id, score)
        md = certificate_to_markdown(cert)
        assert "AI Literacy Completion Certificate" in md
        assert "Alice" in md
        assert "Acme GmbH" in md
        assert cert["certificate_id"] in md
        assert "PASSED" in md

    def test_failed_result_reflected_in_markdown(self):
        module = MODULES[0]
        answers = {q["id"]: (q["correct"] + 1) % len(q["options"]) for q in module["questions"]}
        score = score_answers(module["id"], answers)
        cert = build_certificate("Alice", "Acme", module["id"], score)
        md = certificate_to_markdown(cert)
        assert "NOT PASSED" in md
